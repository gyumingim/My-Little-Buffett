<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$shared/api';
  import { Loading, Card, Button } from '$shared/ui';

  interface StockResult {
    rank: number;
    corp_code: string;
    corp_name: string;
    stock_code: string;
    sector: string;
    total_score: number;
    signal: string;
    indicators: Record<string, { value: number; grade: string }>;
  }

  interface ScreenerData {
    total_analyzed: number;
    year: string;
    stocks: StockResult[];
  }

  let loading = true;
  let error = '';
  let data: ScreenerData | null = null;
  let year = '2023';
  let fsDiv = 'CFS';
  let limit = 30;

  const years = ['2023', '2022', '2021', '2020'];

  onMount(async () => {
    await fetchStocks();
  });

  async function fetchStocks() {
    loading = true;
    error = '';

    try {
      const response = await api.screenerV2(year, fsDiv, limit);
      if (response.success && response.data) {
        data = response.data as ScreenerData;
      } else {
        error = response.message || '데이터를 가져오는데 실패했습니다.';
      }
    } catch (e) {
      error = '네트워크 오류가 발생했습니다.';
      console.error(e);
    } finally {
      loading = false;
    }
  }

  function getSignalColor(signal: string): string {
    switch (signal) {
      case '강력매수': return 'signal-strong-buy';
      case '매수': return 'signal-buy';
      case '관망': return 'signal-hold';
      case '매도': return 'signal-sell';
      case '강력매도': return 'signal-strong-sell';
      default: return 'signal-neutral';
    }
  }

  function getGradeColor(grade: string): string {
    switch (grade) {
      case 'A': return 'grade-a';
      case 'B': return 'grade-b';
      case 'C': return 'grade-c';
      case 'D': return 'grade-d';
      case 'F': return 'grade-f';
      default: return '';
    }
  }

  function goToAnalysis(stock: StockResult) {
    goto(`/company/${stock.corp_code}?name=${encodeURIComponent(stock.corp_name)}&year=${year}&fs_div=${fsDiv}`);
  }

  function getScoreColor(score: number): string {
    if (score >= 80) return 'score-excellent';
    if (score >= 65) return 'score-good';
    if (score >= 50) return 'score-average';
    if (score >= 35) return 'score-poor';
    return 'score-bad';
  }
</script>

<svelte:head>
  <title>우량주 스크리너 - My Little Buffett</title>
</svelte:head>

<div class="container">
  <section class="header">
    <h1>우량주 스크리너</h1>
    <p>10개 재무지표 기반 종합 분석</p>
  </section>

  <Card>
    <div class="filters">
      <div class="filter-group">
        <label for="year-select">사업연도</label>
        <select id="year-select" bind:value={year} on:change={fetchStocks}>
          {#each years as y}
            <option value={y}>{y}년</option>
          {/each}
        </select>
      </div>
      <div class="filter-group">
        <label for="fs-select">재무제표</label>
        <select id="fs-select" bind:value={fsDiv} on:change={fetchStocks}>
          <option value="CFS">연결</option>
          <option value="OFS">개별</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="limit-select">기업 수</label>
        <select id="limit-select" bind:value={limit} on:change={fetchStocks}>
          <option value={20}>20개</option>
          <option value={30}>30개</option>
          <option value={50}>50개</option>
          <option value={100}>100개</option>
        </select>
      </div>
    </div>
  </Card>

  {#if loading}
    <div class="loading-section">
      <Loading size="lg" text="분석 중..." />
      <p class="loading-hint">DB 캐시 확인 후 없으면 API 호출 (최초 1회)</p>
    </div>
  {:else if error}
    <Card>
      <div class="error-state">
        <p>{error}</p>
        <Button variant="secondary" on:click={fetchStocks}>다시 시도</Button>
      </div>
    </Card>
  {:else if data}
    <div class="stats">
      <span>분석 완료: <strong>{data.total_analyzed}개</strong> 기업</span>
    </div>

    <div class="legend">
      <h4>지표 등급</h4>
      <div class="legend-items">
        <span class="legend-item"><span class="grade-badge grade-a">A</span> 우수</span>
        <span class="legend-item"><span class="grade-badge grade-b">B</span> 양호</span>
        <span class="legend-item"><span class="grade-badge grade-c">C</span> 보통</span>
        <span class="legend-item"><span class="grade-badge grade-d">D</span> 미흡</span>
        <span class="legend-item"><span class="grade-badge grade-f">F</span> 위험</span>
      </div>
    </div>

    <div class="stock-list">
      {#each data.stocks as stock}
        <button class="stock-card" on:click={() => goToAnalysis(stock)}>
          <div class="rank">#{stock.rank}</div>
          <div class="stock-info">
            <div class="stock-name">{stock.corp_name}</div>
            <div class="stock-meta">
              <span class="stock-code">{stock.stock_code}</span>
              <span class="stock-sector">{stock.sector}</span>
            </div>
          </div>
          <div class="score-section">
            <div class="score {getScoreColor(stock.total_score)}">{stock.total_score}</div>
            <span class="signal-badge {getSignalColor(stock.signal)}">
              {stock.signal}
            </span>
          </div>
          <div class="indicators">
            {#if stock.indicators['ROE (자기자본이익률)']}
              <span class="indicator">
                <span class="ind-label">ROE</span>
                <span class="grade-badge {getGradeColor(stock.indicators['ROE (자기자본이익률)'].grade)}">
                  {stock.indicators['ROE (자기자본이익률)'].grade}
                </span>
              </span>
            {/if}
            {#if stock.indicators['이자보상배율']}
              <span class="indicator">
                <span class="ind-label">이자</span>
                <span class="grade-badge {getGradeColor(stock.indicators['이자보상배율'].grade)}">
                  {stock.indicators['이자보상배율'].grade}
                </span>
              </span>
            {/if}
            {#if stock.indicators['영업이익성장률']}
              <span class="indicator">
                <span class="ind-label">성장</span>
                <span class="grade-badge {getGradeColor(stock.indicators['영업이익성장률'].grade)}">
                  {stock.indicators['영업이익성장률'].grade}
                </span>
              </span>
            {/if}
            {#if stock.indicators['현금흐름질 (버핏지표)']}
              <span class="indicator">
                <span class="ind-label">CF</span>
                <span class="grade-badge {getGradeColor(stock.indicators['현금흐름질 (버핏지표)'].grade)}">
                  {stock.indicators['현금흐름질 (버핏지표)'].grade}
                </span>
              </span>
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}

  <div class="actions">
    <Button variant="secondary" on:click={() => goto('/')}>홈으로</Button>
  </div>
</div>

<style>
  .header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .header h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .header p {
    color: var(--text-secondary);
  }

  .filters {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .filter-group label {
    font-size: 0.875rem;
    font-weight: 500;
  }

  .filter-group select {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    background: white;
    cursor: pointer;
  }

  .loading-section {
    text-align: center;
    padding: 3rem 0;
  }

  .loading-hint {
    margin-top: 1rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .stats {
    margin: 1rem 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .legend {
    background: var(--bg-secondary);
    padding: 0.75rem 1rem;
    border-radius: var(--border-radius);
    margin-bottom: 1rem;
  }

  .legend h4 {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
  }

  .legend-items {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
  }

  .stock-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .stock-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.875rem 1rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    width: 100%;
  }

  .stock-card:hover {
    border-color: var(--color-primary);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .rank {
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-primary);
    min-width: 2.5rem;
  }

  .stock-info {
    flex: 1;
    min-width: 0;
  }

  .stock-name {
    font-weight: 600;
    font-size: 1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .stock-meta {
    display: flex;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .score-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    min-width: 60px;
  }

  .score {
    font-size: 1.25rem;
    font-weight: 700;
    padding: 0.25rem 0.5rem;
    border-radius: var(--border-radius);
  }

  .score-excellent { color: #166534; background: #dcfce7; }
  .score-good { color: #047857; background: #d1fae5; }
  .score-average { color: #92400e; background: #fef3c7; }
  .score-poor { color: #9a3412; background: #ffedd5; }
  .score-bad { color: #991b1b; background: #fee2e2; }

  .signal-badge {
    padding: 0.125rem 0.375rem;
    border-radius: 9999px;
    font-size: 0.625rem;
    font-weight: 600;
  }

  .signal-strong-buy { background: #dcfce7; color: #166534; }
  .signal-buy { background: #d1fae5; color: #047857; }
  .signal-hold { background: #fef3c7; color: #92400e; }
  .signal-sell { background: #fee2e2; color: #991b1b; }
  .signal-strong-sell { background: #fecaca; color: #7f1d1d; }
  .signal-neutral { background: #f3f4f6; color: #4b5563; }

  .indicators {
    display: flex;
    gap: 0.5rem;
  }

  .indicator {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.125rem;
  }

  .ind-label {
    font-size: 0.625rem;
    color: var(--text-secondary);
  }

  .grade-badge {
    width: 1.25rem;
    height: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.25rem;
    font-size: 0.625rem;
    font-weight: 700;
  }

  .grade-a { background: #dcfce7; color: #166534; }
  .grade-b { background: #d1fae5; color: #047857; }
  .grade-c { background: #fef3c7; color: #92400e; }
  .grade-d { background: #ffedd5; color: #9a3412; }
  .grade-f { background: #fee2e2; color: #991b1b; }

  .error-state {
    text-align: center;
    padding: 2rem;
  }

  .error-state p {
    color: var(--color-danger);
    margin-bottom: 1rem;
  }

  .actions {
    display: flex;
    justify-content: center;
    margin-top: 2rem;
  }

  @media (max-width: 768px) {
    .stock-card {
      flex-wrap: wrap;
    }

    .indicators {
      width: 100%;
      justify-content: flex-end;
      margin-top: 0.5rem;
    }
  }
</style>
