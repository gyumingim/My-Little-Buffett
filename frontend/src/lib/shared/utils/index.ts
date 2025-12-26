/**
 * 숫자 포맷팅 유틸리티
 */

/**
 * 금액을 한국어 단위로 포맷팅
 * @example formatAmount(1234567890) => "12억 3,456만"
 */
export function formatAmount(value: number): string {
  if (value === 0) return '0';

  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (absValue >= 1_0000_0000_0000) {
    // 조 단위
    const jo = Math.floor(absValue / 1_0000_0000_0000);
    const eok = Math.floor((absValue % 1_0000_0000_0000) / 1_0000_0000);
    return `${sign}${jo.toLocaleString()}조 ${eok > 0 ? eok.toLocaleString() + '억' : ''}`.trim();
  } else if (absValue >= 1_0000_0000) {
    // 억 단위
    const eok = Math.floor(absValue / 1_0000_0000);
    const man = Math.floor((absValue % 1_0000_0000) / 1_0000);
    return `${sign}${eok.toLocaleString()}억 ${man > 0 ? man.toLocaleString() + '만' : ''}`.trim();
  } else if (absValue >= 1_0000) {
    // 만 단위
    const man = Math.floor(absValue / 1_0000);
    return `${sign}${man.toLocaleString()}만`;
  } else {
    return `${sign}${absValue.toLocaleString()}`;
  }
}

/**
 * 퍼센트 포맷팅
 */
export function formatPercent(value: number, decimals: number = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

/**
 * 배수 포맷팅
 */
export function formatRatio(value: number, decimals: number = 2): string {
  if (value >= 999) return '999+배';
  return `${value.toFixed(decimals)}배`;
}

/**
 * Signal 타입을 한글로 변환
 */
export function signalToKorean(signal: string): string {
  const mapping: Record<string, string> = {
    'strong_buy': '강력 매수',
    'buy': '매수',
    'hold': '관망',
    'caution': '주의',
    'sell': '매도',
    'strong_sell': '강력 매도'
  };
  return mapping[signal] || signal;
}

/**
 * Signal 타입을 CSS 클래스로 변환
 */
export function signalToClass(signal: string): string {
  const mapping: Record<string, string> = {
    'strong_buy': 'signal-strong-buy',
    'buy': 'signal-buy',
    'hold': 'signal-hold',
    'caution': 'signal-caution',
    'sell': 'signal-sell',
    'strong_sell': 'signal-strong-sell'
  };
  return mapping[signal] || '';
}

/**
 * 점수에 따른 색상 반환
 */
export function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--signal-strong-buy)';
  if (score >= 60) return 'var(--signal-buy)';
  if (score >= 40) return 'var(--signal-hold)';
  if (score >= 20) return 'var(--signal-sell)';
  return 'var(--signal-strong-sell)';
}
