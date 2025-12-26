<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$shared/api';
  import { Loading, Card, Button } from '$shared/ui';

  interface StockResult {
    corp_code: string;
    corp_name: string;
    stock_code: string;
    score: number;
    signal: string;
    recommendation: string;
    cash_generation: string | null;
    interest_coverage: number | null;
    operating_growth: number | null;
  }

  let loading = true;
  let error = '';
  let stocks: StockResult[] = [];
  let year = new Date().getFullYear().toString();
  let fsDiv = 'OFS';

  const years = Array.from({ length: 5 }, (_, i) => (new Date().getFullYear() - i).toString());

  onMount(async () => {
    await fetchStocks();
  });

  async function fetchStocks() {
    loading = true;
    error = '';

    try {
      const response = await api.scanStocks(year, fsDiv, 15);
      if (response.success && response.data) {
        stocks = response.data as StockResult[];
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

  function getSignalClass(signal: string): string {
    switch (signal) {
      case 'strong_buy': return 'signal-strong-buy';
      case 'buy': return 'signal-buy';
      case 'hold': return 'signal-hold';
      case 'sell': return 'signal-sell';
      case 'strong_sell': return 'signal-strong-sell';
      default: return 'signal-neutral';
    }
  }

  function getSignalLabel(signal: string): string {
    switch (signal) {
      case 'strong_buy': return '강력 매수';
      case 'buy': return '매수';
      case 'hold': return '보유';
      case 'sell': return '매도';
      case 'strong_sell': return '강력 매도';
      default: return '중립';
    }
  }

  function goToAnalysis(stock: StockResult) {
    goto(`/company/${stock.corp_code}?name=${encodeURIComponent(stock.corp_name)}&year=${year}&fs_div=${fsDiv}`);
  }
</script>

<svelte:head>
  <title>우량주 스크리너 - My Little Buffett</title>
</svelte:head>

<div class="container">
  <section class="header">
    <h1>우량주 스크리너</h1>
    <p>5대 지표 기준 상위 종목을 확인하세요</p>
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
          <option value="OFS">개별</option>
          <option value="CFS">연결</option>
        </select>
      </div>
    </div>
  </Card>

  {#if loading}
    <Loading size="lg" text="분석 중..." />
  {:else if error}
    <Card>
      <div class="error-state">
        <p>{error}</p>
        <Button variant="secondary" on:click={fetchStocks}>다시 시도</Button>
      </div>
    </Card>
  {:else}
    <div class="stock-list">
      {#each stocks as stock, i}
        <button class="stock-card" on:click={() => goToAnalysis(stock)}>
          <div class="rank">#{i + 1}</div>
          <div class="stock-info">
            <div class="stock-name">{stock.corp_name}</div>
            <div class="stock-code">{stock.stock_code}</div>
          </div>
          <div class="score-section">
            <div class="score">{stock.score}</div>
            <span class="signal-badge {getSignalClass(stock.signal)}">
              {getSignalLabel(stock.signal)}
            </span>
          </div>
          <div class="metrics">
            {#if stock.interest_coverage !== null}
              <span class="metric">이자보상 {stock.interest_coverage.toFixed(1)}배</span>
            {/if}
            {#if stock.operating_growth !== null}
              <span class="metric">성장률 {stock.operating_growth > 0 ? '+' : ''}{stock.operating_growth.toFixed(1)}%</span>
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

  .stock-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 1.5rem;
  }

  .stock-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.25rem;
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
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .rank {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--color-primary);
    min-width: 3rem;
  }

  .stock-info {
    flex: 1;
  }

  .stock-name {
    font-weight: 600;
    font-size: 1.125rem;
  }

  .stock-code {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .score-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .score {
    font-size: 1.5rem;
    font-weight: 700;
  }

  .signal-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .signal-strong-buy { background: #dcfce7; color: #166534; }
  .signal-buy { background: #d1fae5; color: #047857; }
  .signal-hold { background: #fef3c7; color: #92400e; }
  .signal-sell { background: #fee2e2; color: #991b1b; }
  .signal-strong-sell { background: #fecaca; color: #7f1d1d; }
  .signal-neutral { background: #f3f4f6; color: #4b5563; }

  .metrics {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 120px;
  }

  .metric {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

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

    .metrics {
      width: 100%;
      flex-direction: row;
      gap: 1rem;
      margin-top: 0.5rem;
    }
  }
</style>
