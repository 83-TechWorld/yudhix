import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type BotState = 'awake' | 'asleep' | 'offline' | 'connecting';

const LABELS: Record<BotState, string> = {
  awake: 'AI is awake: claims are checked by the local AI model',
  asleep: 'AI is asleep: using rule-based checks (no AI model available)',
  offline: "Can't reach the Yudhix API",
  connecting: 'Connecting…',
};

/**
 * A small robot that shows the AI engine's state.
 *   awake      eyes open, antenna light pulsing
 *   asleep     eyes closed, floating "z"s (rule-based mode)
 *   offline    x eyes (API unreachable)
 *   connecting dim, no animation
 */
@Component({
  selector: 'y-bot',
  template: `
    <svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 32 32" role="img" [attr.aria-label]="label()"
      [class]="'bot ' + state()">
      <title>{{ label() }}</title>
      <!-- antenna -->
      <line x1="16" y1="4.5" x2="16" y2="8" class="stroke" />
      <circle cx="16" cy="3.5" r="2" class="light" />
      <!-- head -->
      <rect x="5" y="8" width="22" height="17" rx="5.5" class="head" />
      <rect x="2.5" y="13.5" width="2.5" height="6" rx="1.25" class="ear" />
      <rect x="27" y="13.5" width="2.5" height="6" rx="1.25" class="ear" />
      @switch (state()) {
        @case ('awake') {
          <g class="eyes"><circle cx="11.5" cy="15.5" r="2.3" class="eye" /><circle cx="20.5" cy="15.5" r="2.3" class="eye" /></g>
          <path d="M12.5 20.5 Q16 23 19.5 20.5" class="stroke mouth" />
        }
        @case ('asleep') {
          <path d="M9.3 15.8 Q11.5 17.6 13.7 15.8" class="stroke lid" />
          <path d="M18.3 15.8 Q20.5 17.6 22.7 15.8" class="stroke lid" />
          <line x1="14" y1="21" x2="18" y2="21" class="stroke mouth" />
        }
        @case ('offline') {
          <path d="M9.8 13.8 l3.4 3.4 M13.2 13.8 l-3.4 3.4 M18.8 13.8 l3.4 3.4 M22.2 13.8 l-3.4 3.4" class="stroke" />
          <path d="M12.5 22 Q16 19.8 19.5 22" class="stroke mouth" />
        }
        @default {
          <circle cx="11.5" cy="15.5" r="1.6" class="eye dim" /><circle cx="20.5" cy="15.5" r="1.6" class="eye dim" />
        }
      }
    </svg>
    @if (state() === 'asleep') {
      <span class="zz" aria-hidden="true"><i>z</i><i>z</i><i>z</i></span>
    }
  `,
  styles: `
    :host { position: relative; display: inline-flex; line-height: 0; }
    .head { fill: var(--surface-2); stroke: currentColor; stroke-width: 1.6; }
    .ear { fill: currentColor; opacity: .55; }
    .stroke { fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; }
    .light { fill: currentColor; }
    .eye { fill: currentColor; }

    .bot.awake { color: var(--ok); }
    .bot.awake .light { animation: glow 2.4s ease-in-out infinite; }
    .bot.awake .eyes { transform-origin: 16px 15.5px; animation: blink 4.5s infinite; }
    .bot.asleep { color: var(--text-3); }
    .bot.asleep .light { opacity: .35; }
    .bot.asleep .head { animation: breathe 3.2s ease-in-out infinite; transform-origin: 16px 25px; }
    .bot.offline { color: var(--danger); }
    .bot.connecting { color: var(--text-3); opacity: .6; }
    .dim { opacity: .5; }

    @keyframes glow { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
    @keyframes blink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(.1); } }
    @keyframes breathe { 0%, 100% { transform: scaleY(1); } 50% { transform: scaleY(.96); } }

    .zz { position: absolute; top: -9px; right: -8px; display: flex; gap: 0; pointer-events: none; }
    .zz i { font: 700 8px/1 var(--font); font-style: normal; color: var(--text-3); opacity: 0; animation: float-z 2.4s ease-in infinite; }
    .zz i:nth-child(2) { font-size: 9.5px; animation-delay: .8s; }
    .zz i:nth-child(3) { font-size: 11px; animation-delay: 1.6s; }
    @keyframes float-z { 0% { opacity: 0; transform: translate(0, 4px); } 30% { opacity: .9; } 100% { opacity: 0; transform: translate(4px, -8px); } }

    @media (prefers-reduced-motion: reduce) {
      .bot *, .zz i { animation: none !important; }
      .zz i { opacity: .8; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BotStatusComponent {
  readonly state = input<BotState>('connecting');
  readonly size = input(22);
  protected readonly label = computed(() => LABELS[this.state()]);
}
