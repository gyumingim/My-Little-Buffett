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
    stocks: Stock[];
    filtered_out: Stock[];
    no_data_corps: string[];
  }

  let loading = true;
  let error = '';
  let data: ScreenerData | null = null;
  let showFilteredOut = false;

  // 필터 옵션
  let year = '2024';
  let fsDiv = 'CFS';
  let limit = 100;

  const yearOptions = ['2024', '2023', '2022', '2021'];
  const limitOptions = [50, 100, 150, 200, 250];

  onMount(async () => {
    await fetchData();
  });

  async function fetchData() {
    loading = true;
    error = '';

    try {
      const response = await api.screenerV2(year, fsDiv, limit);

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

  function goToCompany(stock: Stock) {
    goto(`/company/${stock.corp_code}?name=${encodeURIComponent(stock.corp_name)}&year=${year}&fs_div=${fsDiv}`);
  }

  function getSignalColor(signal: string): string {
    switch (signal) {
      case '강력매수': return 'signal-strong-buy';
      case '매수': return 'signal-buy';
      case '관망': return 'signal-hold';
      case '매도': return 'signal-sell';
      case '강력매도': return 'signal-strong-sell';
      case '투자부적격': return 'signal-disqualified';
      default: return 'signal-neutral';
    }
  }

  function getScoreColor(score: number): string {
    if (score >= 80) return 'score-excellent';
    if (score >= 65) return 'score-good';
    if (score >= 50) return 'score-average';
    if (score >= 35) return 'score-poor';
    return 'score-bad';
  }

  function getGradeClass(grade: string): string {
    switch (grade) {
      case 'A': return 'grade-a';
      case 'B': return 'grade-b';
      case 'C': return 'grade-c';
      case 'D': return 'grade-d';
      case 'F': return 'grade-f';
      default: return '';
    }
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
        <select id="year" bind:value={year} on:change={fetchData}>
          {#each yearOptions as y}
            <option value={y}>{y}년</option>
          {/each}
        </select>
      </div>

      <div class="filter-group">
        <label for="fs_div">재무제표</label>
        <select id="fs_div" bind:value={fsDiv} on:change={fetchData}>
          <option value="CFS">연결</option>
          <option value="OFS">개별</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="limit">분석 수</label>
        <select id="limit" bind:value={limit} on:change={fetchData}>
          {#each limitOptions as l}
            <option value={l}>{l}개</option>
          {/each}
        </select>
      </div>

      <Button variant="primary" on:click={fetchData}>
        분석 시작
      </Button>
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
  {:else if data}
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
      <h4>버핏 채점 기준 (100점)</h4>
      <div class="legend-items">
        <span class="legend-item roe">ROE 30점</span>
        <span class="legend-item ocf">현금창출 25점</span>
        <span class="legend-item growth">성장성 20점</span>
        <span class="legend-item safety">안정성 25점</span>
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
                {#each Object.entries(stock.indicators) as [name, ind]}
                  <td class="indicator-col">
                    <span class="grade-mini {getGradeClass(ind.grade)}">{ind.grade}</span>
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
  .score-excellent { background: #dcfce7; color: #166534; }
  .score-good { background: #d1fae5; color: #047857; }
  .score-average { background: #fef3c7; color: #92400e; }
  .score-poor { background: #ffedd5; color: #9a3412; }
  .score-bad { background: #fee2e2; color: #991b1b; }

  .signal-strong-buy { background: #dcfce7; color: #166534; }
  .signal-buy { background: #d1fae5; color: #047857; }
  .signal-hold { background: #fef3c7; color: #92400e; }
  .signal-sell { background: #fee2e2; color: #991b1b; }
  .signal-strong-sell { background: #fecaca; color: #7f1d1d; }
  .signal-disqualified { background: #f3f4f6; color: #6b7280; }

  .grade-a { background: #dcfce7; color: #166534; }
  .grade-b { background: #d1fae5; color: #047857; }
  .grade-c { background: #fef3c7; color: #92400e; }
  .grade-d { background: #ffedd5; color: #9a3412; }
  .grade-f { background: #fee2e2; color: #991b1b; }

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
  }
</style>
