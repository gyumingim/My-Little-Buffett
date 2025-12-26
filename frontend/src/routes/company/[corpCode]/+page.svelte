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
    max_score: number;
    grade: string;
    description: string;
    good_criteria: string;
    category: string;
  }

  interface AnalysisData {
    corp_code: string;
    corp_name: string;
    year: string;
    fs_div: string;
    total_score: number;
    signal: string;
    recommendation: string;
    filter_passed: boolean;
    filter_reasons: string[];
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
      case '투자부적격': return 'signal-disqualified';
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
    const val = indicator.value;
    if (val === 999) return '∞';
    if (indicator.name.includes('배율')) {
      return val.toFixed(1) + '배';
    } else if (indicator.name.includes('률') || indicator.name.includes('율') || indicator.name.includes('비율')) {
      return val.toFixed(1) + '%';
    } else if (indicator.name.includes('창출력')) {
      return val.toFixed(2) + '배';
    }
    return val.toFixed(1);
  }

  function getCategoryIcon(category: string): string {
    switch (category) {
      case '수익성': return '💰';
      case '현금창출': return '💵';
      case '성장성': return '📈';
      case '안정성': return '🛡️';
      default: return '📊';
    }
  }

  function getCategoryColor(category: string): string {
    switch (category) {
      case '수익성': return 'cat-profit';
      case '현금창출': return 'cat-cash';
      case '성장성': return 'cat-growth';
      case '안정성': return 'cat-safety';
      default: return '';
    }
  }
</script>

<svelte:head>
  <title>{corpName || '기업'} 버핏 분석 - My Little Buffett</title>
</svelte:head>

<div class="container">
  {#if loading}
    <div class="loading-section">
      <Loading size="lg" text="버핏 기준으로 분석 중..." />
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

    <!-- 필터링 실패 경고 -->
    {#if !analysis.filter_passed}
      <div class="filter-warning">
        <h3>⚠️ 투자 부적격 판정</h3>
        <p>버핏의 안전마진 기준을 통과하지 못했습니다:</p>
        <ul>
          {#each analysis.filter_reasons as reason}
            <li>{reason}</li>
          {/each}
        </ul>
      </div>
    {/if}

    <!-- 종합 점수 카드 -->
    <Card>
      <div class="score-card">
        <div class="score-main">
          <div class="total-score {getScoreColor(analysis.total_score)}" class:disqualified={!analysis.filter_passed}>
            {analysis.filter_passed ? analysis.total_score : 0}
          </div>
          <div class="score-label">/ 100점</div>
        </div>
        <div class="signal-section">
          <span class="signal-badge {getSignalColor(analysis.signal)}">
            {analysis.signal}
          </span>
          <p class="recommendation">{analysis.recommendation}</p>
        </div>
      </div>
    </Card>

    <!-- 점수 배분 안내 -->
    <div class="scoring-info">
      <h4>버핏형 채점 기준 (100점 만점)</h4>
      <div class="scoring-breakdown">
        <span class="scoring-item cat-profit">💰 ROE 30점</span>
        <span class="scoring-item cat-cash">💵 현금창출 25점</span>
        <span class="scoring-item cat-growth">📈 성장성 20점</span>
        <span class="scoring-item cat-safety">🛡️ 안정성 25점</span>
      </div>
    </div>

    <!-- 지표 섹션 -->
    <div class="indicators-section">
      <h2>5대 핵심 지표 상세</h2>

      <div class="indicators-grid">
        {#each analysis.indicators as indicator}
          <div class="indicator-card {getCategoryColor(indicator.category)}">
            <div class="indicator-header">
              <span class="indicator-icon">{getCategoryIcon(indicator.category)}</span>
              <div class="indicator-title">
                <h3 class="indicator-name">{indicator.name}</h3>
                <span class="indicator-category">{indicator.category}</span>
              </div>
              <div class="indicator-grade">
                <span class="grade-badge {getGradeColor(indicator.grade)}">{indicator.grade}</span>
              </div>
            </div>

            <div class="indicator-score-bar">
              <div class="score-bar-bg">
                <div
                  class="score-bar-fill {getScoreColor(indicator.score / indicator.max_score * 100)}"
                  style="width: {(indicator.score / indicator.max_score) * 100}%"
                ></div>
              </div>
              <span class="score-text">{indicator.score} / {indicator.max_score}점</span>
            </div>

            <div class="indicator-value-row">
              <span class="value-label">측정값</span>
              <span class="value-number">
                {formatValue(indicator)}
              </span>
            </div>

            <div class="indicator-description">
              <p class="what-is">{indicator.description}</p>
            </div>

            <div class="indicator-criteria">
              <span class="criteria-label">버핏 기준</span>
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
    margin-bottom: 1.5rem;
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

  /* 필터링 경고 */
  .filter-warning {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--border-radius-lg);
    padding: 1.25rem;
    margin-bottom: 1.5rem;
  }

  .filter-warning h3 {
    color: #991b1b;
    margin: 0 0 0.5rem;
    font-size: 1rem;
  }

  .filter-warning p {
    color: #b91c1c;
    margin: 0 0 0.5rem;
    font-size: 0.875rem;
  }

  .filter-warning ul {
    margin: 0;
    padding-left: 1.25rem;
  }

  .filter-warning li {
    color: #dc2626;
    font-size: 0.875rem;
    margin-bottom: 0.25rem;
  }

  /* 종합 점수 카드 */
  .score-card {
    display: flex;
    align-items: center;
    gap: 2rem;
    padding: 1.5rem;
  }

  .score-main {
    text-align: center;
  }

  .total-score {
    font-size: 3.5rem;
    font-weight: 800;
    padding: 1rem 1.5rem;
    border-radius: var(--border-radius-lg);
    min-width: 100px;
  }

  .total-score.disqualified {
    background: #f3f4f6 !important;
    color: #9ca3af !important;
    text-decoration: line-through;
  }

  .score-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
  }

  .signal-section {
    flex: 1;
  }

  .signal-badge {
    display: inline-block;
    padding: 0.5rem 1.5rem;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 1.25rem;
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
  .signal-disqualified { background: #f3f4f6; color: #6b7280; }
  .signal-neutral { background: #f3f4f6; color: #4b5563; }

  /* 점수 색상 */
  .score-excellent { color: #166534; background: #dcfce7; }
  .score-good { color: #047857; background: #d1fae5; }
  .score-average { color: #92400e; background: #fef3c7; }
  .score-poor { color: #9a3412; background: #ffedd5; }
  .score-bad { color: #991b1b; background: #fee2e2; }

  /* 점수 배분 안내 */
  .scoring-info {
    background: var(--bg-secondary);
    padding: 1rem 1.25rem;
    border-radius: var(--border-radius);
    margin: 1.5rem 0;
  }

  .scoring-info h4 {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
  }

  .scoring-breakdown {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .scoring-item {
    font-size: 0.8125rem;
    padding: 0.25rem 0.75rem;
    border-radius: var(--border-radius);
    font-weight: 500;
  }

  /* 카테고리 색상 */
  .cat-profit { background: #fef3c7; color: #92400e; }
  .cat-cash { background: #d1fae5; color: #047857; }
  .cat-growth { background: #dbeafe; color: #1d4ed8; }
  .cat-safety { background: #f3e8ff; color: #7c3aed; }

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
    border-left: 4px solid transparent;
  }

  .indicator-card.cat-profit { border-left-color: #f59e0b; }
  .indicator-card.cat-cash { border-left-color: #10b981; }
  .indicator-card.cat-growth { border-left-color: #3b82f6; }
  .indicator-card.cat-safety { border-left-color: #8b5cf6; }

  .indicator-card:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }

  .indicator-header {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .indicator-icon {
    font-size: 1.5rem;
  }

  .indicator-title {
    flex: 1;
  }

  .indicator-name {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
  }

  .indicator-category {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .indicator-grade {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .grade-badge {
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 700;
  }

  .grade-a { background: #dcfce7; color: #166534; }
  .grade-b { background: #d1fae5; color: #047857; }
  .grade-c { background: #fef3c7; color: #92400e; }
  .grade-d { background: #ffedd5; color: #9a3412; }
  .grade-f { background: #fee2e2; color: #991b1b; }

  /* 점수 바 */
  .indicator-score-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .score-bar-bg {
    flex: 1;
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
  }

  .score-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s;
  }

  .score-bar-fill.score-excellent { background: #22c55e; }
  .score-bar-fill.score-good { background: #10b981; }
  .score-bar-fill.score-average { background: #f59e0b; }
  .score-bar-fill.score-poor { background: #f97316; }
  .score-bar-fill.score-bad { background: #ef4444; }

  .score-text {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-secondary);
    white-space: nowrap;
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
    font-size: 1.25rem;
    font-weight: 700;
  }

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

    .scoring-breakdown {
      flex-direction: column;
      gap: 0.5rem;
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
