<script>
  import { onMount } from 'svelte';

  let loading = false;
  let error = null;
  let backtestResult = null;

  // 설정
  let selectedYear = '2023';
  let selectedFsDiv = 'CFS';
  let topN = 20;
  let holdingYears = 1;

  const fsDivOptions = [
    { value: 'CFS', label: '연결재무제표' },
    { value: 'OFS', label: '개별재무제표' }
  ];

  const years = Array.from({ length: 7 }, (_, i) => (2018 + i).toString());

  async function runBacktest() {
    loading = true;
    error = null;
    backtestResult = null;

    try {
      const params = new URLSearchParams({
        year: selectedYear,
        fs_div: selectedFsDiv,
        top_n: topN.toString(),
        holding_years: holdingYears.toString()
      });

      const response = await fetch(`/api/backtest/validate?${params}`);
      const data = await response.json();

      if (data.success) {
        backtestResult = data.data;
      } else {
        error = data.message;
      }
    } catch (e) {
      error = `백테스팅 실행 중 오류: ${e.message}`;
    } finally {
      loading = false;
    }
  }

  function getReturnClass(returnRate) {
    if (returnRate >= 50) return 'return-excellent';
    if (returnRate >= 20) return 'return-good';
    if (returnRate >= 0) return 'return-positive';
    if (returnRate >= -20) return 'return-negative';
    return 'return-bad';
  }
</script>

<svelte:head>
  <title>백테스팅 - My Little Buffett</title>
</svelte:head>

<div class="container">
  <h1>📊 전략 백테스팅</h1>
  <p class="subtitle">과거 지표로 선정된 종목들이 실제로 수익률이 좋았는지 검증합니다</p>

  <div class="config-panel">
    <h2>백테스팅 설정</h2>

    <div class="form-grid">
      <div class="form-group">
        <label for="year">분석 연도</label>
        <select id="year" bind:value={selectedYear}>
          {#each years as year}
            <option value={year}>{year}년</option>
          {/each}
        </select>
      </div>

      <div class="form-group">
        <label for="fs_div">재무제표 구분</label>
        <select id="fs_div" bind:value={selectedFsDiv}>
          {#each fsDivOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>

      <div class="form-group">
        <label for="top_n">상위 종목 수</label>
        <input type="number" id="top_n" bind:value={topN} min="5" max="100" />
      </div>

      <div class="form-group">
        <label for="holding_years">보유 기간 (년)</label>
        <input type="number" id="holding_years" bind:value={holdingYears} min="1" max="10" />
      </div>
    </div>

    <button class="run-btn" on:click={runBacktest} disabled={loading}>
      {loading ? '분석 중...' : '백테스팅 실행'}
    </button>
  </div>

  {#if error}
    <div class="error-box">
      <p>{error}</p>
    </div>
  {/if}

  {#if backtestResult}
    <div class="results">
      <h2>백테스팅 결과</h2>

      <!-- 통계 요약 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">평균 수익률</div>
          <div class="stat-value {getReturnClass(backtestResult.statistics.avg_return)}">
            {backtestResult.statistics.avg_return.toFixed(2)}%
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-label">KOSPI 수익률</div>
          <div class="stat-value {getReturnClass(backtestResult.statistics.kospi_return)}">
            {backtestResult.statistics.kospi_return.toFixed(2)}%
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-label">초과 수익률 (Alpha)</div>
          <div class="stat-value {getReturnClass(backtestResult.statistics.alpha)}">
            {backtestResult.statistics.alpha >= 0 ? '+' : ''}{backtestResult.statistics.alpha.toFixed(2)}%
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-label">승률</div>
          <div class="stat-value">
            {backtestResult.statistics.win_rate.toFixed(1)}%
          </div>
          <div class="stat-detail">
            ({backtestResult.statistics.win_count} / {backtestResult.statistics.valid_stocks})
          </div>
        </div>
      </div>

      <!-- 기간 정보 -->
      <div class="period-info">
        <p>
          <strong>분석 기간:</strong>
          {backtestResult.config.buy_date} → {backtestResult.config.sell_date}
          ({backtestResult.config.holding_years}년)
        </p>
        <p>
          <strong>대상:</strong>
          {backtestResult.config.year}년 {backtestResult.config.fs_div} 기준 상위 {backtestResult.config.top_n}개 종목
        </p>
      </div>

      <!-- 종목별 상세 결과 -->
      <div class="stocks-table">
        <h3>종목별 수익률</h3>
        <table>
          <thead>
            <tr>
              <th>순위</th>
              <th>종목명</th>
              <th>종목코드</th>
              <th>당시 점수</th>
              <th>매수가</th>
              <th>매도가</th>
              <th>수익률</th>
            </tr>
          </thead>
          <tbody>
            {#each backtestResult.stocks as stock, idx}
              <tr>
                <td>{idx + 1}</td>
                <td class="stock-name">{stock.corp_name}</td>
                <td>{stock.stock_code}</td>
                <td>{stock.total_score}</td>
                {#if stock.error}
                  <td colspan="3" class="error-cell">{stock.error}</td>
                {:else}
                  <td>{stock.buy_price.toLocaleString()}원</td>
                  <td>{stock.sell_price.toLocaleString()}원</td>
                  <td class="{getReturnClass(stock.return_rate)}">
                    {stock.return_rate >= 0 ? '+' : ''}{stock.return_rate.toFixed(2)}%
                  </td>
                {/if}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- 해석 가이드 -->
      <div class="guide">
        <h3>💡 결과 해석</h3>
        <ul>
          <li><strong>평균 수익률:</strong> 상위 {backtestResult.config.top_n}개 종목에 균등 투자했을 때의 평균 수익률</li>
          <li><strong>초과 수익률 (Alpha):</strong> KOSPI 대비 얼마나 더 벌었는가 (양수면 시장 수익률 초과)</li>
          <li><strong>승률:</strong> 수익률이 플러스(+)인 종목의 비율</li>
          <li><strong>주의:</strong> 과거 성과가 미래 수익을 보장하지 않습니다</li>
        </ul>
      </div>
    </div>
  {/if}
</div>

<style>
  .container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
  }

  h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: #1f2937;
  }

  .subtitle {
    color: #6b7280;
    margin-bottom: 2rem;
  }

  .config-panel {
    background: white;
    border-radius: 8px;
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .config-panel h2 {
    font-size: 1.25rem;
    margin-bottom: 1.5rem;
    color: #374151;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
  }

  .form-group label {
    font-size: 0.875rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #374151;
  }

  .form-group select,
  .form-group input {
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    font-size: 1rem;
  }

  .run-btn {
    background: #2563eb;
    color: white;
    padding: 0.75rem 2rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .run-btn:hover:not(:disabled) {
    background: #1d4ed8;
  }

  .run-btn:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }

  .error-box {
    background: #fee2e2;
    border: 1px solid #fca5a5;
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 2rem;
    color: #991b1b;
  }

  .results {
    background: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .results h2 {
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    color: #1f2937;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .stat-card {
    background: #f9fafb;
    padding: 1.5rem;
    border-radius: 6px;
    text-align: center;
  }

  .stat-label {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 0.5rem;
  }

  .stat-value {
    font-size: 1.875rem;
    font-weight: 700;
  }

  .stat-detail {
    font-size: 0.875rem;
    color: #6b7280;
    margin-top: 0.5rem;
  }

  .return-excellent {
    color: #047857;
  }

  .return-good {
    color: #059669;
  }

  .return-positive {
    color: #10b981;
  }

  .return-negative {
    color: #dc2626;
  }

  .return-bad {
    color: #991b1b;
    font-weight: 800;
  }

  .period-info {
    background: #eff6ff;
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 2rem;
    border-left: 4px solid #2563eb;
  }

  .period-info p {
    margin: 0.5rem 0;
    color: #1e40af;
  }

  .stocks-table {
    margin-bottom: 2rem;
  }

  .stocks-table h3 {
    font-size: 1.125rem;
    margin-bottom: 1rem;
    color: #374151;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  thead {
    background: #f9fafb;
  }

  th {
    padding: 0.75rem;
    text-align: left;
    font-size: 0.875rem;
    font-weight: 600;
    color: #6b7280;
    border-bottom: 2px solid #e5e7eb;
  }

  td {
    padding: 0.75rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .stock-name {
    font-weight: 600;
    color: #1f2937;
  }

  .error-cell {
    color: #dc2626;
    font-size: 0.875rem;
    text-align: center;
  }

  tbody tr:hover {
    background: #f9fafb;
  }

  .guide {
    background: #fef3c7;
    padding: 1.5rem;
    border-radius: 6px;
    border-left: 4px solid #f59e0b;
  }

  .guide h3 {
    font-size: 1.125rem;
    margin-bottom: 1rem;
    color: #92400e;
  }

  .guide ul {
    margin: 0;
    padding-left: 1.5rem;
    color: #78350f;
  }

  .guide li {
    margin-bottom: 0.5rem;
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    h1 {
      font-size: 1.5rem;
    }

    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    table {
      font-size: 0.875rem;
    }

    th, td {
      padding: 0.5rem 0.25rem;
    }
  }
</style>
