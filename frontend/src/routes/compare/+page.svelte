<script lang="ts">
  import { api } from '$shared/api';
  import { Card, Button, Loading } from '$shared/ui';

  interface Company {
    corp_code: string;
    corp_name: string;
    stock_code: string;
    sector: string;
  }

  interface CompareResult {
    company1: { info: Company; analysis: any };
    company2: { info: Company; analysis: any };
    comparison: { score_diff: number; winner: string };
  }

  let searchQuery1 = '';
  let searchQuery2 = '';
  let searchResults1: Company[] = [];
  let searchResults2: Company[] = [];
  let showResults1 = false;
  let showResults2 = false;

  let company1: Company | null = null;
  let company2: Company | null = null;

  let bsnsYear = new Date().getFullYear().toString();
  let fsDiv = 'OFS';

  let loading = false;
  let result: CompareResult | null = null;
  let error = '';

  const years = Array.from({ length: 5 }, (_, i) => (new Date().getFullYear() - i).toString());

  let searchTimeout1: ReturnType<typeof setTimeout>;
  let searchTimeout2: ReturnType<typeof setTimeout>;

  async function handleSearch1() {
    if (searchQuery1.length < 1) {
      searchResults1 = [];
      showResults1 = false;
      return;
    }
    clearTimeout(searchTimeout1);
    searchTimeout1 = setTimeout(async () => {
      const res = await api.searchCompanies(searchQuery1, 5);
      if (res.success && res.data) {
        searchResults1 = res.data as Company[];
        showResults1 = searchResults1.length > 0;
      }
    }, 200);
  }

  async function handleSearch2() {
    if (searchQuery2.length < 1) {
      searchResults2 = [];
      showResults2 = false;
      return;
    }
    clearTimeout(searchTimeout2);
    searchTimeout2 = setTimeout(async () => {
      const res = await api.searchCompanies(searchQuery2, 5);
      if (res.success && res.data) {
        searchResults2 = res.data as Company[];
        showResults2 = searchResults2.length > 0;
      }
    }, 200);
  }

  function selectCompany1(c: Company) {
    company1 = c;
    searchQuery1 = c.corp_name;
    showResults1 = false;
  }

  function selectCompany2(c: Company) {
    company2 = c;
    searchQuery2 = c.corp_name;
    showResults2 = false;
  }

  async function handleCompare() {
    if (!company1 || !company2) {
      alert('두 기업을 선택해주세요.');
      return;
    }

    loading = true;
    error = '';
    result = null;

    try {
      const res = await api.compareCompanies(company1.corp_code, company2.corp_code, bsnsYear, fsDiv);
      if (res.success && res.data) {
        result = res.data as CompareResult;
      } else {
        error = res.message || '비교 분석에 실패했습니다.';
      }
    } catch (e) {
      error = '네트워크 오류가 발생했습니다.';
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
</script>

<svelte:head>
  <title>기업 비교 - My Little Buffett</title>
</svelte:head>

<div class="container">
  <section class="header">
    <h1>기업 비교</h1>
    <p>두 기업의 5대 지표를 비교해보세요</p>
  </section>

  <Card>
    <div class="compare-form">
      <div class="company-selectors">
        <div class="selector">
          <label for="company1">기업 1</label>
          <div class="search-wrapper">
            <input
              id="company1"
              type="text"
              placeholder="기업명 검색"
              bind:value={searchQuery1}
              on:input={handleSearch1}
              on:focus={() => showResults1 = searchResults1.length > 0}
            />
            {#if showResults1}
              <div class="search-dropdown">
                {#each searchResults1 as c}
                  <button type="button" on:click={() => selectCompany1(c)}>
                    {c.corp_name} <span>{c.stock_code}</span>
                  </button>
                {/each}
              </div>
            {/if}
          </div>
          {#if company1}
            <span class="selected">{company1.corp_name} ({company1.sector})</span>
          {/if}
        </div>

        <div class="vs">VS</div>

        <div class="selector">
          <label for="company2">기업 2</label>
          <div class="search-wrapper">
            <input
              id="company2"
              type="text"
              placeholder="기업명 검색"
              bind:value={searchQuery2}
              on:input={handleSearch2}
              on:focus={() => showResults2 = searchResults2.length > 0}
            />
            {#if showResults2}
              <div class="search-dropdown">
                {#each searchResults2 as c}
                  <button type="button" on:click={() => selectCompany2(c)}>
                    {c.corp_name} <span>{c.stock_code}</span>
                  </button>
                {/each}
              </div>
            {/if}
          </div>
          {#if company2}
            <span class="selected">{company2.corp_name} ({company2.sector})</span>
          {/if}
        </div>
      </div>

      <div class="options">
        <select bind:value={bsnsYear}>
          {#each years as y}
            <option value={y}>{y}년</option>
          {/each}
        </select>
        <select bind:value={fsDiv}>
          <option value="OFS">개별</option>
          <option value="CFS">연결</option>
        </select>
        <Button variant="primary" on:click={handleCompare}>비교 분석</Button>
      </div>
    </div>
  </Card>

  {#if loading}
    <Loading size="lg" text="분석 중..." />
  {:else if error}
    <Card>
      <p class="error">{error}</p>
    </Card>
  {:else if result}
    <div class="result-grid">
      <Card>
        <div class="company-result" class:winner={result.comparison.winner === result.company1.info.corp_name}>
          <h3>{result.company1.info.corp_name}</h3>
          {#if result.company1.analysis}
            <div class="score">{result.company1.analysis.overall_score}</div>
            <span class="signal {getSignalClass(result.company1.analysis.overall_signal)}">
              {getSignalLabel(result.company1.analysis.overall_signal)}
            </span>
            <p class="recommendation">{result.company1.analysis.recommendation}</p>
          {:else}
            <p class="no-data">분석 데이터 없음</p>
          {/if}
        </div>
      </Card>

      <Card>
        <div class="company-result" class:winner={result.comparison.winner === result.company2.info.corp_name}>
          <h3>{result.company2.info.corp_name}</h3>
          {#if result.company2.analysis}
            <div class="score">{result.company2.analysis.overall_score}</div>
            <span class="signal {getSignalClass(result.company2.analysis.overall_signal)}">
              {getSignalLabel(result.company2.analysis.overall_signal)}
            </span>
            <p class="recommendation">{result.company2.analysis.recommendation}</p>
          {:else}
            <p class="no-data">분석 데이터 없음</p>
          {/if}
        </div>
      </Card>
    </div>

    {#if result.company1.analysis && result.company2.analysis}
      <Card title="지표 비교">
        <table class="compare-table">
          <thead>
            <tr>
              <th>지표</th>
              <th>{result.company1.info.corp_name}</th>
              <th>{result.company2.info.corp_name}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>종합 점수</td>
              <td class:better={result.company1.analysis.overall_score > result.company2.analysis.overall_score}>
                {result.company1.analysis.overall_score}점
              </td>
              <td class:better={result.company2.analysis.overall_score > result.company1.analysis.overall_score}>
                {result.company2.analysis.overall_score}점
              </td>
            </tr>
            {#if result.company1.analysis.interest_coverage && result.company2.analysis.interest_coverage}
              <tr>
                <td>이자보상배율</td>
                <td class:better={result.company1.analysis.interest_coverage.ratio > result.company2.analysis.interest_coverage.ratio}>
                  {result.company1.analysis.interest_coverage.ratio.toFixed(2)}배
                </td>
                <td class:better={result.company2.analysis.interest_coverage.ratio > result.company1.analysis.interest_coverage.ratio}>
                  {result.company2.analysis.interest_coverage.ratio.toFixed(2)}배
                </td>
              </tr>
            {/if}
            {#if result.company1.analysis.operating_profit_growth && result.company2.analysis.operating_profit_growth}
              <tr>
                <td>영업이익 성장률</td>
                <td class:better={result.company1.analysis.operating_profit_growth.growth_rate > result.company2.analysis.operating_profit_growth.growth_rate}>
                  {result.company1.analysis.operating_profit_growth.growth_rate.toFixed(1)}%
                </td>
                <td class:better={result.company2.analysis.operating_profit_growth.growth_rate > result.company1.analysis.operating_profit_growth.growth_rate}>
                  {result.company2.analysis.operating_profit_growth.growth_rate.toFixed(1)}%
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </Card>
    {/if}
  {/if}

  <div class="actions">
    <Button variant="secondary" on:click={() => history.back()}>돌아가기</Button>
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
  }

  .header p {
    color: var(--text-secondary);
  }

  .compare-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .company-selectors {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
  }

  .selector {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .selector label {
    font-weight: 500;
  }

  .search-wrapper {
    position: relative;
  }

  .search-wrapper input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 1rem;
  }

  .search-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 0 0 var(--border-radius) var(--border-radius);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    z-index: 10;
  }

  .search-dropdown button {
    width: 100%;
    padding: 0.75rem;
    text-align: left;
    border: none;
    background: white;
    cursor: pointer;
  }

  .search-dropdown button:hover {
    background: var(--bg-tertiary);
  }

  .search-dropdown button span {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-left: 0.5rem;
  }

  .selected {
    font-size: 0.875rem;
    color: var(--color-primary);
  }

  .vs {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-secondary);
    padding-top: 1.5rem;
  }

  .options {
    display: flex;
    gap: 1rem;
    align-items: center;
    justify-content: center;
  }

  .options select {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    background: white;
  }

  .result-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 2rem;
  }

  .company-result {
    text-align: center;
    padding: 1rem;
  }

  .company-result.winner {
    background: linear-gradient(to bottom, #dcfce7, transparent);
    border-radius: var(--border-radius);
  }

  .company-result h3 {
    font-size: 1.25rem;
    margin-bottom: 0.5rem;
  }

  .score {
    font-size: 3rem;
    font-weight: 700;
    color: var(--color-primary);
  }

  .signal {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 600;
    margin: 0.5rem 0;
  }

  .signal-strong-buy { background: #dcfce7; color: #166534; }
  .signal-buy { background: #d1fae5; color: #047857; }
  .signal-hold { background: #fef3c7; color: #92400e; }
  .signal-sell { background: #fee2e2; color: #991b1b; }
  .signal-strong-sell { background: #fecaca; color: #7f1d1d; }
  .signal-neutral { background: #f3f4f6; color: #4b5563; }

  .recommendation {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .no-data {
    color: var(--text-secondary);
  }

  .error {
    color: var(--color-danger);
    text-align: center;
  }

  .compare-table {
    width: 100%;
    border-collapse: collapse;
  }

  .compare-table th,
  .compare-table td {
    padding: 0.75rem;
    text-align: center;
    border-bottom: 1px solid var(--border-color);
  }

  .compare-table th {
    background: var(--bg-tertiary);
    font-weight: 600;
  }

  .compare-table td:first-child {
    text-align: left;
    font-weight: 500;
  }

  .compare-table td.better {
    color: #166534;
    font-weight: 600;
  }

  .actions {
    display: flex;
    justify-content: center;
    margin-top: 2rem;
  }

  @media (max-width: 768px) {
    .company-selectors {
      flex-direction: column;
    }

    .vs {
      text-align: center;
      padding: 0.5rem 0;
    }

    .result-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
