<script>
  let corpCode = '';
  let results = null;
  let loading = false;
  let error = null;

  const API_BASE = 'http://localhost:8000';

  async function analyzeSingle() {
    if (!corpCode.trim()) {
      error = '기업 코드를 입력해주세요.';
      return;
    }

    loading = true;
    error = null;
    results = null;

    try {
      const response = await fetch(`${API_BASE}/api/analyze/${corpCode.trim()}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      results = [data];
    } catch (e) {
      error = `분석 실패: ${e.message}`;
    } finally {
      loading = false;
    }
  }

  async function analyzeTop50() {
    loading = true;
    error = null;
    results = null;

    try {
      const response = await fetch(`${API_BASE}/api/top/50?min_score=0`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      results = data.results || [];
    } catch (e) {
      error = `분석 실패: ${e.message}`;
    } finally {
      loading = false;
    }
  }

  function getGradeClass(grade) {
    return `grade grade-${grade.replace('+', '\\+')}`;
  }
</script>

<div class="container">
  <div class="header">
    <h1>🐂 My Little Buffett</h1>
    <p>Alpha Finder - 상장폐지 안 당할 주식 찾기</p>
  </div>

  <div class="search-box">
    <h2>기업 분석</h2>
    <div class="input-group">
      <input
        type="text"
        bind:value={corpCode}
        placeholder="기업 코드 입력 (예: 00100601)"
        on:keypress={(e) => e.key === 'Enter' && analyzeSingle()}
      />
      <button class="btn btn-primary" on:click={analyzeSingle}>
        단일 분석
      </button>
    </div>
    <button class="btn btn-secondary" on:click={analyzeTop50} style="margin-top: 10px;">
      상위 50개 종목 분석
    </button>
  </div>

  {#if loading}
    <div class="loading">
      분석 중...
    </div>
  {/if}

  {#if error}
    <div class="error">
      {error}
    </div>
  {/if}

  {#if results && results.length > 0}
    <div class="results">
      <h2>분석 결과 ({results.length}개)</h2>

      {#each results as company}
        <div class="company-card">
          <div class="company-header">
            <span class="company-code">{company.corp_code}</span>
            <span class={getGradeClass(company.grade)}>{company.grade}</span>
          </div>

          <div class="score">
            점수: {company.final_score}점
          </div>

          <div class="recommendation">
            {company.recommendation}
          </div>

          {#if company.stage2_score}
            <div class="details">
              <div class="detail-section">
                <h4>현금 창출력</h4>
                <p>{company.stage2_score.breakdown.cash.score}점 - {company.stage2_score.breakdown.cash.reason}</p>
              </div>

              <div class="detail-section">
                <h4>자회사 건전성</h4>
                <p>{company.stage2_score.breakdown.subsidiary.score}점 - {company.stage2_score.breakdown.subsidiary.reason}</p>
              </div>

              <div class="detail-section">
                <h4>사업 확장성</h4>
                <p>{company.stage2_score.breakdown.expansion.score}점 - {company.stage2_score.breakdown.expansion.reason}</p>
              </div>

              <div class="detail-section">
                <h4>주주 환원 의지</h4>
                <p>{company.stage2_score.breakdown.shareholder.score}점 - {company.stage2_score.breakdown.shareholder.reason}</p>
              </div>
            </div>
          {/if}

          {#if company.stage3_boost && company.stage3_boost.total_boost > 0}
            <div class="details">
              <h4>부스터 (+{company.stage3_boost.total_boost}점)</h4>
              {#each Object.values(company.stage3_boost.boosters) as booster}
                {#if booster.boost > 0}
                  <p>• {booster.reason} (+{booster.boost}점)</p>
                {/if}
              {/each}
            </div>
          {/if}

          {#if company.stage1_filter && !company.stage1_filter.passed}
            <div class="details">
              <h4 style="color: #f44336;">⚠️ 위험 요소</h4>
              {#each Object.values(company.stage1_filter.filters) as filter}
                {#if !filter.passed}
                  <p style="color: #f44336;">• {filter.reason}</p>
                {/if}
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
