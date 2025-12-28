<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
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
    stocks: Stock[];
    filtered_out: Stock[];
    total_analyzed: number;
    from_cache: boolean;
  }

  let loading = false;
  let error = '';
  let data: ScreenerData | null = null;

  // 설정
  let year = '2024';
  let limit = 100;
  let batchSize = 100;

  const yearOptions = ['2024', '2023', '2022', '2021', '2020'];
  const limitOptions = [10, 50, 100, 500, 1000, 2000, 4000];

  async function analyze() {
    loading = true;
    error = '';

    try {
      const response = await fetch(
        `/api/indicators/screener?year=${year}&limit=${limit}&batch_size=${batchSize}`,
        { method: 'GET' }
      );
      const result = await response.json();

      if (result.success && result.data) {
        data = result.data as ScreenerData;
      } else {
        error = result.message || '분석 실패';
      }
    } catch (e) {
      error = '네트워크 오류';
      console.error(e);
    } finally {
      loading = false;
    }
  }

  function goToCompany(stock: Stock) {
    goto(`/company/${stock.corp_code}?year=${year}`);
  }

  function getScoreColor(score: number): string {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#3b82f6';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
  }
</script>

<div class="screener-container">
  <Card>
    <div class="header">
      <h1>🎯 버핏형 우량주 스크리너</h1>
      <p class="subtitle">워런 버핏의 가치투자 원칙 기반 - 한 번에 모든 것 처리</p>
    </div>

    <div class="controls">
      <div class="control-group">
        <label for="year">사업연도</label>
        <select id="year" bind:value={year}>
          {#each yearOptions as y}
            <option value={y}>{y}년</option>
          {/each}
        </select>
      </div>

      <div class="control-group">
        <label for="limit">분석 개수</label>
        <select id="limit" bind:value={limit}>
          {#each limitOptions as l}
            <option value={l}>{l}개</option>
          {/each}
        </select>
      </div>

      <div class="control-group">
        <label for="batch_size">배치 크기</label>
        <input type="number" id="batch_size" bind:value={batchSize} min="10" max="500" />
      </div>
    </div>

    <div class="action-section">
      <Button on:click={analyze} disabled={loading} variant="primary" fullWidth>
        {loading ? '분석 중...' : '🚀 분석 시작'}
      </Button>
    </div>

    {#if error}
      <div class="error-box">
        ❌ {error}
      </div>
    {/if}

    {#if data}
      <div class="results">
        <div class="stats">
          <div class="stat-item">
            <span class="stat-value">{data.stocks.length}</span>
            <span class="stat-label">우량주</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{data.filtered_out.length}</span>
            <span class="stat-label">필터 탈락</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{data.total_analyzed}</span>
            <span class="stat-label">총 분석</span>
          </div>
          <div class="stat-item">
            <span class="stat-badge">{data.from_cache ? '캐시' : '신규'}</span>
          </div>
        </div>

        {#if data.stocks.length > 0}
          <div class="stock-list">
            {#each data.stocks as stock}
              <div class="stock-card" on:click={() => goToCompany(stock)} role="button" tabindex="0">
                <div class="stock-header">
                  <div class="stock-info">
                    <span class="rank">#{stock.rank}</span>
                    <span class="name">{stock.corp_name}</span>
                    <span class="code">{stock.stock_code}</span>
                  </div>
                  <div class="score" style="color: {getScoreColor(stock.total_score)}">
                    {stock.total_score.toFixed(1)}점
                  </div>
                </div>
                <div class="stock-details">
                  <span class="signal">{stock.signal}</span>
                  <span class="sector">{stock.sector}</span>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty">
            <p>필터를 통과한 우량주가 없습니다.</p>
          </div>
        {/if}
      </div>
    {/if}
  </Card>
</div>

<style>
  .screener-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
  }

  .header {
    text-align: center;
    margin-bottom: 30px;
  }

  h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 10px;
  }

  .subtitle {
    color: #666;
    font-size: 0.95rem;
  }

  .controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  label {
    font-weight: 600;
    font-size: 0.9rem;
  }

  select, input {
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 1rem;
  }

  .action-section {
    margin: 20px 0;
  }

  .error-box {
    background: #fee;
    border: 1px solid #fcc;
    color: #c33;
    padding: 15px;
    border-radius: 6px;
    margin: 15px 0;
  }

  .results {
    margin-top: 30px;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin-bottom: 25px;
  }

  .stat-item {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
  }

  .stat-value {
    display: block;
    font-size: 1.8rem;
    font-weight: 700;
    color: #3b82f6;
  }

  .stat-label {
    display: block;
    font-size: 0.85rem;
    color: #666;
    margin-top: 5px;
  }

  .stat-badge {
    display: inline-block;
    padding: 8px 16px;
    background: #10b981;
    color: white;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .stock-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .stock-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 15px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .stock-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
    transform: translateY(-2px);
  }

  .stock-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .stock-info {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .rank {
    font-weight: 700;
    color: #3b82f6;
    font-size: 1.1rem;
  }

  .name {
    font-weight: 600;
    font-size: 1.05rem;
  }

  .code {
    color: #666;
    font-size: 0.9rem;
  }

  .score {
    font-size: 1.4rem;
    font-weight: 700;
  }

  .stock-details {
    display: flex;
    gap: 15px;
    font-size: 0.9rem;
    color: #666;
  }

  .signal {
    font-weight: 600;
  }

  .empty {
    text-align: center;
    padding: 40px;
    color: #999;
  }

  @media (max-width: 768px) {
    .stats {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
