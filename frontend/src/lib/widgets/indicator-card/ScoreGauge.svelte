<script lang="ts">
  import { getScoreColor, signalToKorean, signalToClass } from '$shared/utils';

  export let score: number;
  export let signal: string;
  export let recommendation: string;

  $: color = getScoreColor(score);
  $: circumference = 2 * Math.PI * 54;
  $: offset = circumference - (score / 100) * circumference;
</script>

<div class="score-container">
  <div class="gauge-wrapper">
    <svg viewBox="0 0 120 120" class="gauge">
      <circle
        cx="60"
        cy="60"
        r="54"
        fill="none"
        stroke="var(--border-color)"
        stroke-width="8"
      />
      <circle
        cx="60"
        cy="60"
        r="54"
        fill="none"
        stroke={color}
        stroke-width="8"
        stroke-linecap="round"
        stroke-dasharray={circumference}
        stroke-dashoffset={offset}
        transform="rotate(-90 60 60)"
        class="gauge-progress"
      />
    </svg>
    <div class="score-text">
      <span class="score-value" style="color: {color}">{score.toFixed(0)}</span>
      <span class="score-label">점</span>
    </div>
  </div>

  <div class="signal-info">
    <span class="signal-badge {signalToClass(signal)}">
      {signalToKorean(signal)}
    </span>
    <p class="recommendation">{recommendation}</p>
  </div>
</div>

<style>
  .score-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    padding: 1.5rem;
  }

  .gauge-wrapper {
    position: relative;
    width: 160px;
    height: 160px;
  }

  .gauge {
    width: 100%;
    height: 100%;
  }

  .gauge-progress {
    transition: stroke-dashoffset 1s ease-out;
  }

  .score-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
  }

  .score-value {
    font-size: 2.5rem;
    font-weight: 700;
    line-height: 1;
  }

  .score-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .signal-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    text-align: center;
  }

  .signal-badge {
    padding: 0.5rem 1rem;
    border-radius: 9999px;
    font-size: 1rem;
    font-weight: 600;
  }

  .recommendation {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
    max-width: 280px;
    line-height: 1.5;
  }
</style>
