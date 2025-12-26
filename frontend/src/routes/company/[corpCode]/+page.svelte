<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$shared/api';
  import { Loading, Card, Button } from '$shared/ui';
  import { addToWatchlist, removeFromWatchlist, isInWatchlist } from '$shared/utils';

  interface Indicator {
    name: string;
    value: number;
    score: number;
    grade: string;
    description: string;
    good_criteria: string;
    trend?: string;
  }

  interface AnalysisData {
    corp_code: string;
    corp_name: string;
    year: string;
    fs_div: string;
    total_score: number;
    signal: string;
    recommendation: string;
    indicators: Indicator[];
    analysis_date: string;
  }

  let loading = true;
  let error = '';
  let analysis: AnalysisData | null = null;
  let inWatchlist = false;

  let corpCode: string;
  let corpName: string;
  let bsnsYear: string;
  let fsDiv: string;

  $: corpCode = $page.params.corpCode ?? '';
  $: corpName = $page.url.searchParams.get('name') ?? '';
  $: bsnsYear = $page.url.searchParams.get('year') ?? '2023';
  $: fsDiv = $page.url.searchParams.get('fs_div') ?? 'CFS';

  onMount(async () => {
    inWatchlist = isInWatchlist(corpCode);
    await fetchData();
  });

  function toggleWatchlist() {
    if (inWatchlist) {
      removeFromWatchlist(corpCode);
    } else {
      addToWatchlist({ corp_code: corpCode, corp_name: corpName, stock_code: '' });
    }
    inWatchlist = !inWatchlist;
  }

  async function fetchData() {
    loading = true;
    error = '';

    try {
      const response = await api.getAnalysisV2(corpCode, corpName, bsnsYear, fsDiv);

      if (response.success && response.data) {
        analysis = response.data as AnalysisData;
      } else {
        error = response.message || '분석 데이터를 가져오는데 실패했습니다.';
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

  function getScoreColor(score: number): string {
    if (score >= 80) return 'score-excellent';
    if (score >= 65) return 'score-good';
    if (score >= 50) return 'score-average';
    if (score >= 35) return 'score-poor';
    return 'score-bad';
  }

  function formatValue(indicator: Indicator): string {
    const name = indicator.name;
    const val = indicator.value;

    if (name.includes('배율')) {
      return val.toFixed(2) + '배';
    } else if (name.includes('률') || name.includes('율')) {
      return val.toFixed(2) + '%';
    } else if (name.includes('비율')) {
      return val.toFixed(2) + '%';
    }
    return val.toFixed(2);
  }

  function getTrendIcon(trend?: string): string {
    if (!trend) return '';
    switch (trend) {
      case 'up': return '↑';
      case 'down': return '↓';
      default: return '→';
    }
  }

  function getTrendClass(trend?: string): string {
    if (!trend) return '';
    switch (trend) {
      case 'up': return 'trend-up';
      case 'down': return 'trend-down';
      default: return 'trend-stable';
    }
  }

  function getCategoryIcon(name: string): string {
    if (name.includes('ROE') || name.includes('마진') || name.includes('이익')) return '💰';
    if (name.includes('부채') || name.includes('이자') || name.includes('유동')) return '🏦';
    if (name.includes('성장')) return '📈';
    if (name.includes('현금')) return '💵';
    return '📊';
  }
</script>

<svelte:head>
  <title>{corpName || '기업'} 분석 결과 - My Little Buffett</title>
</svelte:head>

<div class="container">
  {#if loading}
    <div class="loading-section">
      <Loading size="lg" text="분석 중입니다..." />
      <p class="loading-hint">재무제표 데이터를 분석하고 있습니다</p>
    </div>
  {:else if error}
    <Card>
      <div class="error-state">
        <p class="error-message">{error}</p>
        <Button variant="secondary" on:click={() => history.back()}>돌아가기</Button>
      </div>
    </Card>
  {:else if analysis}
    <div class="analysis-header">
      <div class="company-info">
        <div class="title-row">
          <h1>{analysis.corp_name}</h1>
          <button class="watchlist-btn" class:active={inWatchlist} on:click={toggleWatchlist}>
            {inWatchlist ? '★' : '☆'}
          </button>
        </div>
        <p class="meta">
          {analysis.year}년 {analysis.fs_div === 'CFS' ? '연결' : '개별'} 재무제표 기준
        </p>
      </div>
      <p class="analysis-date">분석일: {analysis.analysis_date}</p>
    </div>

    <!-- 종합 점수 카드 -->
    <Card>
      <div class="score-card">
        <div class="score-main">
          <div class="total-score {getScoreColor(analysis.total_score)}">
            {analysis.total_score}
          </div>
          <div class="score-label">종합 점수</div>
        </div>
        <div class="signal-section">
          <span class="signal-badge {getSignalColor(analysis.signal)}">
            {analysis.signal}
          </span>
          <p class="recommendation">{analysis.recommendation}</p>
        </div>
      </div>
    </Card>

    <!-- 등급 범례 -->
    <div class="legend">
      <h4>지표 등급 안내</h4>
      <div class="legend-items">
        <span class="legend-item"><span class="grade-badge grade-a">A</span> 우수 (80+)</span>
        <span class="legend-item"><span class="grade-badge grade-b">B</span> 양호 (65-79)</span>
        <span class="legend-item"><span class="grade-badge grade-c">C</span> 보통 (50-64)</span>
        <span class="legend-item"><span class="grade-badge grade-d">D</span> 미흡 (35-49)</span>
        <span class="legend-item"><span class="grade-badge grade-f">F</span> 위험 (0-34)</span>
      </div>
    </div>

    <!-- 지표 섹션 -->
    <div class="indicators-section">
      <h2>10대 재무 지표 상세 분석</h2>

      <div class="indicators-grid">
        {#each analysis.indicators as indicator}
          <div class="indicator-card">
            <div class="indicator-header">
              <span class="indicator-icon">{getCategoryIcon(indicator.name)}</span>
              <h3 class="indicator-name">{indicator.name}</h3>
              <div class="indicator-grade">
                <span class="grade-badge {getGradeColor(indicator.grade)}">{indicator.grade}</span>
                <span class="score-small {getScoreColor(indicator.score)}">{indicator.score}점</span>
              </div>
            </div>

            <div class="indicator-value-row">
              <span class="value-label">측정값</span>
              <span class="value-number {getTrendClass(indicator.trend)}">
                {formatValue(indicator)}
                {#if indicator.trend}
                  <span class="trend-icon">{getTrendIcon(indicator.trend)}</span>
                {/if}
              </span>
            </div>

            <div class="indicator-description">
              <p class="what-is">{indicator.description}</p>
            </div>

            <div class="indicator-criteria">
              <span class="criteria-label">좋은 기준</span>
              <span class="criteria-value">{indicator.good_criteria}</span>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="actions">
      <Button variant="secondary" on:click={() => goto('/screener')}>
        스크리너로
      </Button>
      <Button variant="secondary" on:click={() => history.back()}>
        다른 기업 분석
      </Button>
      <Button variant="primary" on:click={() => window.print()}>
        결과 출력
      </Button>
    </div>
  {/if}
</div>

<style>
  .loading-section {
    text-align: center;
    padding: 3rem 0;
  }

  .loading-hint {
    margin-top: 1rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .analysis-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .company-info h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
  }

  .watchlist-btn {
    font-size: 1.5rem;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-secondary);
    transition: color 0.2s;
  }

  .watchlist-btn:hover {
    color: var(--color-primary);
  }

  .watchlist-btn.active {
    color: #fbbf24;
  }

  .meta {
    color: var(--text-secondary);
    margin: 0.5rem 0 0;
  }

  .analysis-date {
    color: var(--text-muted);
    font-size: 0.875rem;
  }

  /* 종합 점수 카드 */
  .score-card {
    display: flex;
    align-items: center;
    gap: 2rem;
    padding: 1rem;
  }

  .score-main {
    text-align: center;
  }

  .total-score {
    font-size: 3rem;
    font-weight: 800;
    padding: 1rem 1.5rem;
    border-radius: var(--border-radius-lg);
  }

  .score-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
  }

  .signal-section {
    flex: 1;
  }

  .signal-badge {
    display: inline-block;
    padding: 0.5rem 1.25rem;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 1.125rem;
  }

  .recommendation {
    margin-top: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  /* 시그널 색상 */
  .signal-strong-buy { background: #dcfce7; color: #166534; }
  .signal-buy { background: #d1fae5; color: #047857; }
  .signal-hold { background: #fef3c7; color: #92400e; }
  .signal-sell { background: #fee2e2; color: #991b1b; }
  .signal-strong-sell { background: #fecaca; color: #7f1d1d; }
  .signal-neutral { background: #f3f4f6; color: #4b5563; }

  /* 점수 색상 */
  .score-excellent { color: #166534; background: #dcfce7; }
  .score-good { color: #047857; background: #d1fae5; }
  .score-average { color: #92400e; background: #fef3c7; }
  .score-poor { color: #9a3412; background: #ffedd5; }
  .score-bad { color: #991b1b; background: #fee2e2; }

  /* 범례 */
  .legend {
    background: var(--bg-secondary);
    padding: 1rem 1.25rem;
    border-radius: var(--border-radius);
    margin: 1.5rem 0;
  }

  .legend h4 {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
  }

  .legend-items {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.8125rem;
  }

  /* 지표 섹션 */
  .indicators-section {
    margin-top: 2rem;
  }

  .indicators-section h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
  }

  .indicators-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 1rem;
  }

  .indicator-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
    padding: 1.25rem;
    transition: all 0.2s;
  }

  .indicator-card:hover {
    border-color: var(--color-primary);
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }

  .indicator-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .indicator-icon {
    font-size: 1.25rem;
  }

  .indicator-name {
    flex: 1;
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
  }

  .indicator-grade {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .grade-badge {
    width: 1.75rem;
    height: 1.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 700;
  }

  .grade-a { background: #dcfce7; color: #166534; }
  .grade-b { background: #d1fae5; color: #047857; }
  .grade-c { background: #fef3c7; color: #92400e; }
  .grade-d { background: #ffedd5; color: #9a3412; }
  .grade-f { background: #fee2e2; color: #991b1b; }

  .score-small {
    font-size: 0.8125rem;
    font-weight: 600;
    padding: 0.125rem 0.5rem;
    border-radius: var(--border-radius);
  }

  .indicator-value-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: var(--bg-secondary);
    border-radius: var(--border-radius);
    margin-bottom: 0.75rem;
  }

  .value-label {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .value-number {
    font-size: 1.125rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .trend-icon {
    font-size: 0.875rem;
  }

  .trend-up { color: #166534; }
  .trend-down { color: #991b1b; }
  .trend-stable { color: #6b7280; }

  .indicator-description {
    margin-bottom: 0.75rem;
  }

  .what-is {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
  }

  .indicator-criteria {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px dashed var(--border-color);
  }

  .criteria-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .criteria-value {
    font-size: 0.8125rem;
    color: #166534;
    font-weight: 500;
  }

  /* 에러 상태 */
  .error-state {
    text-align: center;
    padding: 2rem;
  }

  .error-message {
    color: var(--color-danger);
    margin-bottom: 1rem;
  }

  /* 액션 버튼 */
  .actions {
    display: flex;
    justify-content: center;
    gap: 1rem;
    margin-top: 3rem;
    padding-bottom: 2rem;
  }

  @media (max-width: 768px) {
    .analysis-header {
      flex-direction: column;
    }

    .company-info h1 {
      font-size: 1.5rem;
    }

    .score-card {
      flex-direction: column;
      text-align: center;
    }

    .indicators-grid {
      grid-template-columns: 1fr;
    }

    .total-score {
      font-size: 2.5rem;
    }

    .actions {
      flex-direction: column;
    }
  }

  @media print {
    .actions {
      display: none;
    }

    .indicator-card {
      break-inside: avoid;
    }
  }
</style>
