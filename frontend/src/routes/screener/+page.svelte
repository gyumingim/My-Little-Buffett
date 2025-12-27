<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$shared/api';
  import { Loading, Card, Button } from '$shared/ui';

  interface Stock {
    rank: number;
    corp_code: string;
    corp_name: string;
    stock_code: string;
    sector: string;
    total_score: number;
    signal: string;
    filter_passed: boolean;
    filter_reasons: string[];
    indicators: Record<string, { value: number; score: number; max_score: number; grade: string }>;
  }

  interface ScreenerData {
    year: string;
    total_analyzed: number;
    passed_count: number;
    filtered_count: number;
    no_data_count: number;
    from_cache: boolean;
    stocks: Stock[];
    filtered_out: Stock[];
    no_data_corps: string[];
  }

  let loading = false;  // 자동 로딩 제거
  let refreshing = false;
  let error = '';
  let data: ScreenerData | null = null;
  let showFilteredOut = false;

  // 필터 옵션
  let year = '2023';
  let fsDiv = 'CFS';
  let limit = 100;
  let useCache = true;

  // API/분석 분리 설정
  let fetching = false;
  let analyzing = false;
  let batchSize = 100;
  let maxConcurrent = 100;
  let showAdvanced = false;

  const yearOptions = ['2024', '2023', '2022', '2021', '2020'];
  const limitOptions = [100, 500, 1000, 2000, 4000];

  // onMount 제거 - 자동 로딩 없음

  async function fetchData() {
    loading = true;
    error = '';

    try {
      const response = await api.screenerV2(year, fsDiv, limit, useCache);

      if (response.success && response.data) {
        data = response.data as ScreenerData;
      } else {
        error = response.message || '스크리닝 데이터를 가져오는데 실패했습니다.';
      }
    } catch (e) {
      error = '네트워크 오류가 발생했습니다.';
      console.error(e);
    } finally {
      loading = false;
    }
  }

  async function refreshData() {
    refreshing = true;
    useCache = false;
    await fetchData();
    useCache = true;
    refreshing = false;
  }

  async function fetchAPIData() {
    fetching = true;
    error = '';

    try {
      const response = await fetch(
        `/api/indicators/v2/fetch?year=${year}&fs_div=${fsDiv}&limit=${limit}&batch_size=${batchSize}&max_concurrent=${maxConcurrent}`,
        { method: 'POST' }
      );
      const result = await response.json();

      const failMsg = result.data.failed_count > 0
        ? `\n\n실패 목록 (처음 10개):\n${result.data.failed_corps.slice(0, 10).join('\n')}`
        : '';

      alert(`API 호출 완료!\n- Fetch: ${result.data.fetched_count}개\n- Skip: ${result.data.skipped_count}개\n- Fail: ${result.data.failed_count}개\n- 시간: ${result.data.elapsed_seconds}초${failMsg}`);

      if (!result.success && result.data.failed_count > 0) {
        console.error('실패한 기업들:', result.data.failed_corps);
        error = `API 호출 실패: ${result.data.failed_count}개 기업 실패`;
      }
    } catch (e) {
      error = '네트워크 오류';
      console.error(e);
    } finally {
      fetching = false;
    }
  }

  async function analyzeData() {
    analyzing = true;
    error = '';

    try {
      const response = await fetch(
        `/api/indicators/v2/analyze?year=${year}&fs_div=${fsDiv}&limit=${limit}&batch_size=${batchSize}`,
        { method: 'POST' }
      );
      const result = await response.json();

      if (result.success) {
        alert(`분석 완료!\n- 통과: ${result.data.passed_count}개\n- 탈락: ${result.data.filtered_count}개\n- CSV 없음: ${result.data.no_csv_count}개\n- 시간: ${result.data.elapsed_seconds}초`);
        // 분석 완료 후 결과 새로고침
        useCache = true;
        await fetchData();
      } else {
        error = result.message || '분석 실패';
      }
    } catch (e) {
      error = '네트워크 오류';
      console.error(e);
    } finally {
      analyzing = false;
    }
  }

  function goToCompany(stock: Stock) {
    goto(`/company/${stock.corp_code}?name=${encodeURIComponent(stock.corp_name)}&year=${year}&fs_div=${fsDiv}`);
  }

  function getSignalColor(signal: string): string {
    if (signal.includes('S급') || signal.includes('강력매수')) return 'signal-strong-buy';
    if (signal.includes('A급') && signal.includes('매수')) return 'signal-buy';
    if (signal.includes('B급') && signal.includes('매수')) return 'signal-buy-weak';
    if (signal.includes('관망')) return 'signal-hold';
    if (signal.includes('D급') || signal.includes('매도')) return 'signal-sell';
    if (signal.includes('F급') || signal.includes('회피')) return 'signal-strong-sell';
    if (signal.includes('투자부적격')) return 'signal-disqualified';
    return 'signal-neutral';
  }

  function getScoreColor(score: number): string {
    if (score >= 90) return 'score-s';
    if (score >= 80) return 'score-excellent';
    if (score >= 65) return 'score-good';
    if (score >= 50) return 'score-average';
    if (score >= 35) return 'score-poor';
    return 'score-bad';
  }

  function getGradeClass(grade: string): string {
    // 세분화된 등급 (S, A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, E+, E, E-, F+, F, F-)
    if (grade === 'S') return 'grade-s';
    if (grade.startsWith('A')) return 'grade-a';
    if (grade.startsWith('B')) return 'grade-b';
    if (grade.startsWith('C')) return 'grade-c';
    if (grade.startsWith('D')) return 'grade-d';
    if (grade.startsWith('E')) return 'grade-e';
    if (grade.startsWith('F')) return 'grade-f';
    return '';
  }
</script>

<svelte:head>
  <title>버핏 스크리너 - My Little Buffett</title>
</svelte:head>

<div class="container">
  <div class="page-header">
    <h1>버핏형 우량주 스크리너</h1>
    <p class="subtitle">워런 버핏의 가치투자 기준으로 선별된 종목</p>
  </div>

  <!-- 필터 섹션 -->
  <Card>
    <div class="filters">
      <div class="filter-group">
        <label for="year">사업연도</label>
        <select id="year" bind:value={year}>
          {#each yearOptions as y}
            <option value={y}>{y}년</option>
          {/each}
        </select>
      </div>

      <div class="filter-group">
        <label for="fs_div">재무제표</label>
        <select id="fs_div" bind:value={fsDiv}>
          <option value="CFS">연결</option>
          <option value="OFS">개별</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="limit">분석 수</label>
        <select id="limit" bind:value={limit}>
          {#each limitOptions as l}
            <option value={l}>{l}개</option>
          {/each}
        </select>
      </div>

      <Button variant="primary" on:click={fetchData}>
        조회
      </Button>
      <Button variant="secondary" on:click={refreshData} disabled={refreshing}>
        {refreshing ? '분석 중...' : '새로 분석'}
      </Button>
    </div>

    <!-- 고급 설정 -->
    <div class="advanced-section">
      <button class="toggle-advanced" on:click={() => showAdvanced = !showAdvanced}>
        {showAdvanced ? '▼' : '▶'} 고급 설정 (API 분리 실행)
      </button>

      {#if showAdvanced}
        <div class="advanced-controls">
          <div class="control-row">
            <div class="control-group">
              <label for="batch_size">배치 크기</label>
              <input type="number" id="batch_size" bind:value={batchSize} min="1" max="500" />
              <span class="control-hint">한 번에 처리할 기업 수</span>
            </div>

            <div class="control-group">
              <label for="max_concurrent">동시 요청 수</label>
              <input type="number" id="max_concurrent" bind:value={maxConcurrent} min="1" max="500" />
              <span class="control-hint">API 동시 호출 수 (높을수록 빠름/불안정)</span>
            </div>
          </div>

          <div class="action-buttons">
            <Button variant="primary" on:click={fetchAPIData} disabled={fetching || analyzing}>
              {fetching ? '호출 중...' : '1️⃣ API 호출 (CSV 저장)'}
            </Button>
            <Button variant="primary" on:click={analyzeData} disabled={fetching || analyzing}>
              {analyzing ? '분석 중...' : '2️⃣ 점수 계산 (CSV 읽기)'}
            </Button>
          </div>

          <!-- 로딩 상태 표시 -->
          {#if fetching}
            <div class="loading-indicator">
              <div class="spinner"></div>
              <span>API 호출 중... ({limit}개 기업 처리)</span>
            </div>
          {/if}

          {#if analyzing}
            <div class="loading-indicator">
              <div class="spinner"></div>
              <span>분석 중... ({limit}개 기업 처리)</span>
            </div>
          {/if}

          <div class="workflow-hint">
            <p><strong>워크플로우:</strong></p>
            <ol>
              <li>API 호출 → DART에서 재무 데이터 받아서 CSV 저장 (느림, 한 번만)</li>
              <li>점수 계산 → CSV 읽어서 버핏 점수 계산 (빠름, 여러 번 가능)</li>
              <li>조회 → 계산된 점수 보기</li>
            </ol>
          </div>
        </div>
      {/if}
    </div>
  </Card>

  {#if loading}
    <div class="loading-section">
      <Loading size="lg" text="버핏 기준으로 분석 중..." />
      <p class="loading-hint">{limit}개 기업을 분석하고 있습니다. 잠시만 기다려주세요.</p>
    </div>
  {:else if error}
    <Card>
      <div class="error-state">
        <p class="error-message">{error}</p>
        <Button variant="secondary" on:click={fetchData}>다시 시도</Button>
      </div>
    </Card>
  {:else if !data}
    <!-- 초기 화면 (데이터 없음) -->
    <Card>
      <div class="empty-state">
        <div class="empty-icon">📊</div>
        <h3>버핏형 우량주 스크리너</h3>
        <p>위에서 조회 조건을 설정하고 "조회" 버튼을 클릭하세요.</p>
        <div class="quick-guide">
          <h4>💡 사용 방법</h4>
          <ul>
            <li><strong>조회:</strong> 저장된 분석 결과 보기 (빠름)</li>
            <li><strong>새로 분석:</strong> 최신 데이터로 재분석 (느림)</li>
            <li><strong>고급 설정:</strong> API 호출과 분석을 분리 실행</li>
          </ul>
        </div>
      </div>
    </Card>
  {:else if data}
    <!-- 캐시 정보 배너 -->
    {#if data.from_cache}
      <div class="cache-banner">
        DB에 저장된 분석 결과입니다. 최신 데이터로 갱신하려면 "새로 분석" 버튼을 클릭하세요.
      </div>
    {/if}

    <!-- 요약 카드 -->
    <div class="summary-cards">
      <div class="summary-card total">
        <span class="summary-value">{data.total_analyzed}</span>
        <span class="summary-label">분석 완료</span>
      </div>
      <div class="summary-card passed">
        <span class="summary-value">{data.passed_count}</span>
        <span class="summary-label">투자적격</span>
      </div>
      <div class="summary-card filtered">
        <span class="summary-value">{data.filtered_count}</span>
        <span class="summary-label">필터링 탈락</span>
      </div>
      <div class="summary-card no-data">
        <span class="summary-value">{data.no_data_count || 0}</span>
        <span class="summary-label">데이터 없음</span>
      </div>
    </div>

    <!-- 채점 기준 안내 -->
    <div class="scoring-legend">
      <h4>버핏 채점 기준 (기본 100점 + 보완 45점)</h4>
      <div class="legend-items">
        <span class="legend-item roe">ROE 30점</span>
        <span class="legend-item ocf">현금창출 25점</span>
        <span class="legend-item growth">성장성 20점</span>
        <span class="legend-item safety">안정성 25점</span>
        <span class="legend-divider">|</span>
        <span class="legend-item roic">ROIC 15점</span>
        <span class="legend-item margin">영업이익률 10점</span>
        <span class="legend-item retention">유보율 10점</span>
        <span class="legend-item stability">안정성 10점</span>
      </div>
    </div>

    <!-- 투자적격 종목 테이블 -->
    <div class="results-section">
      <h2>투자 적격 종목 ({data.stocks.length}개)</h2>

      <div class="table-container">
        <table class="stock-table">
          <thead>
            <tr>
              <th class="rank-col">순위</th>
              <th class="name-col">기업명</th>
              <th class="sector-col">업종</th>
              <th class="score-col">점수</th>
              <th class="signal-col">신호</th>
              <th class="indicator-col">ROE</th>
              <th class="indicator-col">현금</th>
              <th class="indicator-col">성장</th>
              <th class="indicator-col">이자</th>
              <th class="indicator-col">부채</th>
            </tr>
          </thead>
          <tbody>
            {#each data.stocks as stock}
              <tr class="stock-row" on:click={() => goToCompany(stock)}>
                <td class="rank-col">
                  <span class="rank-badge" class:top3={stock.rank <= 3}>{stock.rank}</span>
                </td>
                <td class="name-col">
                  <span class="corp-name">{stock.corp_name}</span>
                  <span class="stock-code">{stock.stock_code}</span>
                </td>
                <td class="sector-col">{stock.sector}</td>
                <td class="score-col">
                  <span class="score-badge {getScoreColor(stock.total_score)}">{stock.total_score}</span>
                </td>
                <td class="signal-col">
                  <span class="signal-badge {getSignalColor(stock.signal)}">{stock.signal}</span>
                </td>
                {#each Object.entries(stock.indicators).slice(0, 5) as [name, ind]}
                  <td class="indicator-col">
                    <span class="grade-mini {getGradeClass(ind.grade)}" title="{name}: {ind.value}">{ind.grade}</span>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- 필터링 탈락 종목 (접기/펴기) -->
    {#if data.filtered_out && data.filtered_out.length > 0}
      <div class="filtered-section">
        <button class="toggle-btn" on:click={() => showFilteredOut = !showFilteredOut}>
          {showFilteredOut ? '▼' : '▶'} 필터링 탈락 종목 ({data.filtered_count}개)
        </button>

        {#if showFilteredOut}
          <div class="filtered-list">
            {#each data.filtered_out as stock}
              <div class="filtered-item" on:click={() => goToCompany(stock)}>
                <div class="filtered-info">
                  <span class="filtered-name">{stock.corp_name}</span>
                  <span class="filtered-sector">{stock.sector}</span>
                </div>
                <div class="filtered-reasons">
                  {#each stock.filter_reasons as reason}
                    <span class="reason-tag">{reason}</span>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  .page-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .page-header h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .subtitle {
    color: var(--text-secondary);
  }

  /* 필터 */
  .filters {
    display: flex;
    gap: 1.5rem;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .filter-group label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .filter-group select {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 0.875rem;
    min-width: 100px;
  }

  /* 로딩 */
  .loading-section {
    text-align: center;
    padding: 4rem 0;
  }

  .loading-hint {
    margin-top: 1rem;
    color: var(--text-secondary);
  }

  /* 에러 */
  .error-state {
    text-align: center;
    padding: 2rem;
  }

  .error-message {
    color: var(--color-danger);
    margin-bottom: 1rem;
  }

  /* 캐시 배너 */
  .cache-banner {
    background: #dbeafe;
    color: #1e40af;
    padding: 0.75rem 1rem;
    border-radius: var(--border-radius);
    margin-bottom: 1rem;
    font-size: 0.875rem;
    text-align: center;
  }

  /* 요약 카드 */
  .summary-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin: 1.5rem 0;
  }

  .summary-card {
    padding: 1.5rem;
    border-radius: var(--border-radius-lg);
    text-align: center;
  }

  .summary-card.total {
    background: #f3f4f6;
  }

  .summary-card.passed {
    background: #dcfce7;
  }

  .summary-card.filtered {
    background: #fee2e2;
  }

  .summary-card.no-data {
    background: #fef3c7;
  }

  .summary-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
  }

  .summary-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  /* 채점 기준 범례 */
  .scoring-legend {
    background: var(--bg-secondary);
    padding: 1rem 1.25rem;
    border-radius: var(--border-radius);
    margin-bottom: 1.5rem;
  }

  .scoring-legend h4 {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
  }

  .legend-items {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .legend-item {
    font-size: 0.8125rem;
    padding: 0.25rem 0.75rem;
    border-radius: var(--border-radius);
    font-weight: 500;
  }

  .legend-item.roe { background: #fef3c7; color: #92400e; }
  .legend-item.ocf { background: #d1fae5; color: #047857; }
  .legend-item.growth { background: #dbeafe; color: #1d4ed8; }
  .legend-item.safety { background: #f3e8ff; color: #7c3aed; }
  .legend-item.roic { background: #fce7f3; color: #be185d; }
  .legend-item.margin { background: #e0e7ff; color: #4338ca; }
  .legend-item.retention { background: #ccfbf1; color: #0d9488; }
  .legend-item.stability { background: #fef9c3; color: #a16207; }
  .legend-divider { color: var(--text-muted); }

  /* 결과 섹션 */
  .results-section h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  /* 테이블 */
  .table-container {
    overflow-x: auto;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
  }

  .stock-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .stock-table th {
    background: var(--bg-secondary);
    padding: 0.75rem;
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
    border-bottom: 1px solid var(--border-color);
  }

  .stock-table td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border-color);
    vertical-align: middle;
  }

  .stock-row {
    cursor: pointer;
    transition: background 0.15s;
  }

  .stock-row:hover {
    background: var(--bg-secondary);
  }

  .rank-col { width: 50px; text-align: center; }
  .name-col { min-width: 120px; }
  .sector-col { width: 80px; }
  .score-col { width: 60px; text-align: center; }
  .signal-col { width: 80px; text-align: center; }
  .indicator-col { width: 50px; text-align: center; }

  .rank-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #e5e7eb;
    font-weight: 600;
    font-size: 0.8125rem;
  }

  .rank-badge.top3 {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: white;
  }

  .corp-name {
    display: block;
    font-weight: 600;
  }

  .stock-code {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .score-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: var(--border-radius);
    font-weight: 700;
    font-size: 0.875rem;
  }

  .signal-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .grade-mini {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
  }

  /* 점수/등급 색상 */
  .score-s { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white; }
  .score-excellent { background: #dcfce7; color: #166534; }
  .score-good { background: #d1fae5; color: #047857; }
  .score-average { background: #fef3c7; color: #92400e; }
  .score-poor { background: #ffedd5; color: #9a3412; }
  .score-bad { background: #fee2e2; color: #991b1b; }

  .signal-strong-buy { background: #dcfce7; color: #166534; }
  .signal-buy { background: #d1fae5; color: #047857; }
  .signal-buy-weak { background: #ecfdf5; color: #059669; }
  .signal-hold { background: #fef3c7; color: #92400e; }
  .signal-sell { background: #fee2e2; color: #991b1b; }
  .signal-strong-sell { background: #fecaca; color: #7f1d1d; }
  .signal-disqualified { background: #f3f4f6; color: #6b7280; }
  .signal-neutral { background: #f3f4f6; color: #6b7280; }

  /* 세분화된 등급 색상 (S~F with +++/++/+/-/--/---) */
  .grade-s {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: white;
    font-weight: 800;
    box-shadow: 0 2px 4px rgba(251, 191, 36, 0.3);
  }
  .grade-a {
    background: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
  }
  .grade-b {
    background: #d1fae5;
    color: #047857;
    border: 1px solid #6ee7b7;
  }
  .grade-c {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fde047;
  }
  .grade-d {
    background: #ffedd5;
    color: #9a3412;
    border: 1px solid #fdba74;
  }
  .grade-e {
    background: #fed7aa;
    color: #c2410c;
    border: 1px solid #fb923c;
  }
  .grade-f {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
  }

  /* 필터링 탈락 섹션 */
  .filtered-section {
    margin-top: 2rem;
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: #f9fafb;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-secondary);
    width: 100%;
    text-align: left;
  }

  .toggle-btn:hover {
    background: #f3f4f6;
  }

  .filtered-list {
    margin-top: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    max-height: 400px;
    overflow-y: auto;
  }

  .filtered-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-color);
    cursor: pointer;
    transition: background 0.15s;
  }

  .filtered-item:last-child {
    border-bottom: none;
  }

  .filtered-item:hover {
    background: #fef2f2;
  }

  .filtered-name {
    font-weight: 600;
    margin-right: 0.5rem;
  }

  .filtered-sector {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .filtered-reasons {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .reason-tag {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    background: #fee2e2;
    color: #991b1b;
    border-radius: var(--border-radius);
  }

  /* 초기 화면 (empty state) */
  .empty-state {
    text-align: center;
    padding: 3rem 2rem;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .empty-state h3 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    color: #1f2937;
  }

  .empty-state > p {
    color: #6b7280;
    margin-bottom: 2rem;
  }

  .quick-guide {
    background: #f9fafb;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: left;
    max-width: 500px;
    margin: 0 auto;
  }

  .quick-guide h4 {
    margin: 0 0 1rem 0;
    color: #374151;
  }

  .quick-guide ul {
    margin: 0;
    padding-left: 1.5rem;
    color: #4b5563;
  }

  .quick-guide li {
    margin-bottom: 0.75rem;
  }

  /* 고급 설정 섹션 */
  .advanced-section {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e5e7eb;
  }

  .toggle-advanced {
    background: none;
    border: none;
    color: #2563eb;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .toggle-advanced:hover {
    color: #1d4ed8;
  }

  .advanced-controls {
    margin-top: 1rem;
    padding: 1.5rem;
    background: #f9fafb;
    border-radius: 8px;
  }

  .control-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .control-group label {
    font-size: 0.875rem;
    font-weight: 600;
    color: #374151;
  }

  .control-group input {
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    font-size: 1rem;
  }

  .control-hint {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .action-buttons {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .workflow-hint {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    padding: 1rem;
    margin-top: 1rem;
  }

  .workflow-hint p {
    margin: 0 0 0.5rem 0;
    color: #92400e;
    font-weight: 600;
  }

  .workflow-hint ol {
    margin: 0;
    padding-left: 1.5rem;
    color: #78350f;
  }

  .workflow-hint li {
    margin-bottom: 0.5rem;
  }

  /* 로딩 인디케이터 스타일 */
  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    margin-top: 1rem;
    background: #f0f9ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    color: #1e40af;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 3px solid #bfdbfe;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 768px) {
    .filters {
      flex-direction: column;
      align-items: stretch;
    }

    .summary-cards {
      grid-template-columns: repeat(2, 1fr);
    }

    .indicator-col {
      display: none;
    }

    .legend-items {
      flex-direction: column;
    }

    .action-buttons {
      flex-direction: column;
    }

    .control-row {
      grid-template-columns: 1fr;
    }
  }
</style>
