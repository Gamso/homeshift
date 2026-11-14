import { css } from "lit";

/** Styles of the HomeShift card (`HomeShiftCard.styles`). */
export const cardStyles = css`
  .calendar-error {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    margin: 0 0 10px;
    padding: 9px 11px;
    border-radius: 10px;
    border: 1px solid rgba(255, 170, 40, 0.45);
    background: rgba(255, 170, 40, 0.13);
    color: #ffd98f;
    font-size: 13px;
    line-height: 1.4;
  }
  .calendar-error ha-icon {
    --mdc-icon-size: 18px;
    flex: none;
    margin-top: 1px;
  }
  .calendar-error strong {
    display: block;
    font-weight: 500;
  }
  .calendar-error span span {
    font-size: 12px;
    color: #e9c486;
  }
  /* Dark glass card: its colour (--m, "r, g, b") follows the thermostat mode. */
  ha-card {
    --m: 148, 163, 184;
    --hs-text: #e6f2f5;
    --hs-text-2: rgba(220, 235, 240, 0.62);
    --hs-surface: rgba(255, 255, 255, 0.06);
    --hs-ring: rgba(255, 255, 255, 0.07);
    /* What the panel and the scheduler card read from the theme follows
       the dark card instead. */
    --primary-text-color: var(--hs-text);
    --secondary-text-color: var(--hs-text-2);
    --divider-color: rgba(255, 255, 255, 0.08);
    --card-background-color: #121a24;
    --ha-card-background: #121a24;
    position: relative;
    /* Clips the glow, the particles and the schedules panel. */
    overflow: hidden;
    padding: 0;
    border-radius: var(--ha-card-border-radius, 20px);
    border: 1px solid rgba(var(--m), 0.25);
    background: linear-gradient(
      160deg,
      rgba(20, 28, 38, 0.96),
      rgba(10, 15, 22, 0.98)
    );
    box-shadow:
      0 8px 26px rgba(0, 0, 0, 0.35),
      0 0 22px -6px rgba(var(--m), 0.45),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
    color: var(--hs-text);
    transition:
      border-color 0.6s,
      box-shadow 0.6s;
  }

  button {
    font-family: inherit;
  }

  button:focus-visible {
    outline: 2px solid #fff;
    outline-offset: 2px;
  }

  /* Ambience: a glow where the heat rises, the cold falls or the air blows. */
  .glow {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(
      110% 70% at 50% 50%,
      rgba(var(--m), 0.22),
      transparent 75%
    );
    animation: breathe 5s ease-in-out infinite;
  }

  ha-card[data-mode="heating"] .glow {
    background: radial-gradient(
      130% 75% at 50% 110%,
      rgba(255, 110, 30, 0.45),
      rgba(255, 80, 20, 0.12) 55%,
      transparent 78%
    );
  }

  ha-card[data-mode="cooling"] .glow {
    background: radial-gradient(
      120% 70% at 50% -10%,
      rgba(80, 190, 255, 0.4),
      rgba(60, 140, 255, 0.1) 55%,
      transparent 75%
    );
  }

  ha-card[data-mode="ventilation"] .glow {
    background: radial-gradient(
      120% 80% at 0% 50%,
      rgba(45, 212, 160, 0.35),
      rgba(45, 212, 160, 0.09) 55%,
      transparent 78%
    );
  }

  ha-card[data-mode="off"] .glow {
    background: radial-gradient(
      110% 70% at 50% 50%,
      rgba(148, 163, 184, 0.18),
      rgba(71, 85, 105, 0.1) 60%,
      transparent 80%
    );
    animation-duration: 9s;
  }

  .particles {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
  }

  .particle {
    position: absolute;
    opacity: 0;
  }

  ha-card[data-mode="heating"] .particle {
    bottom: 0;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: radial-gradient(circle, #ffe0a0, #ff7a2a 60%, transparent 70%);
    box-shadow: 0 0 6px 1px rgba(255, 120, 40, 0.7);
    animation: rise var(--d) ease-in var(--dl) infinite;
  }

  ha-card[data-mode="cooling"] .particle {
    top: 0;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: radial-gradient(circle, #fff, #bfe9ff 55%, transparent 72%);
    animation: fall calc(var(--d) * 1.5) linear var(--dl) infinite;
  }

  ha-card[data-mode="ventilation"] .particle {
    top: var(--y);
    width: 34px;
    height: 2px;
    border-radius: 2px;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(170, 255, 225, 0.75),
      transparent
    );
    animation: breeze var(--d) linear var(--dl) infinite;
  }

  @keyframes breathe {
    50% {
      opacity: 0.6;
    }
  }

  @keyframes rise {
    from {
      transform: translate(0, 0) scale(1);
      opacity: 0.9;
    }
    to {
      transform: translate(var(--dx), -260px) scale(0.3);
      opacity: 0;
    }
  }

  @keyframes fall {
    from {
      transform: translate(0, -10px);
      opacity: 0.9;
    }
    to {
      transform: translate(var(--dx), 320px);
      opacity: 0;
    }
  }

  @keyframes breeze {
    from {
      left: -40px;
      opacity: 0;
    }
    20% {
      opacity: 0.8;
    }
    to {
      left: 100%;
      opacity: 0;
    }
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .container {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
  }

  .rows {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .badge {
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: rgba(var(--m), 0.16);
    box-shadow: inset 0 0 0 1px rgba(var(--m), 0.25);
    color: rgb(var(--m));
    --mdc-icon-size: 21px;
    transition:
      background 0.4s,
      color 0.4s;
  }

  ha-card[data-mode="ventilation"] .badge ha-icon {
    animation: spin 1.6s linear infinite;
  }

  .heading {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.2;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
    font-size: 12px;
    color: var(--hs-text-2);
  }

  .dot {
    flex: none;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgb(var(--m));
    box-shadow: 0 0 6px rgb(var(--m));
  }

  /* Thermostat modes: one segmented control, one colour (--c) per mode. */
  .presets {
    display: flex;
    gap: 4px;
    padding: 3px;
    border-radius: 14px;
    background: rgba(0, 0, 0, 0.28);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
  }

  .preset {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    height: 48px;
    padding: 0 2px;
    border: 0;
    border-radius: 11px;
    background: transparent;
    color: var(--hs-text-2);
    font-size: 11.5px;
    font-weight: 500;
    cursor: pointer;
    --mdc-icon-size: 19px;
    transition:
      background 0.3s,
      color 0.3s,
      box-shadow 0.3s;
  }

  .preset-label {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .preset:hover:not(:disabled):not(.on) {
    background: rgba(255, 255, 255, 0.06);
    color: rgb(var(--c));
  }

  .preset.on {
    color: #fff;
    background: linear-gradient(
      180deg,
      rgba(var(--c), 0.95),
      rgba(var(--c), 0.7)
    );
    box-shadow: 0 3px 12px -2px rgba(var(--c), 0.6);
  }

  .preset:disabled {
    cursor: default;
    opacity: 0.5;
  }

  /* Day mode and next mode, side by side. */
  .tiles {
    position: relative;
    /* The day mode list opens over the rows below. */
    z-index: 2;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
    gap: 6px;
  }

  .tile {
    position: relative;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 8px 10px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
  }

  .tile.day-mode {
    padding: 0;
    background: none;
    box-shadow: none;
  }

  .day-mode-button {
    all: unset;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 3px;
    width: 100%;
    padding: 8px 10px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
    cursor: pointer;
    transition:
      background 0.2s,
      box-shadow 0.2s;
  }

  .day-mode-button:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.09);
  }

  .day-mode-button[aria-expanded="true"] {
    background: rgba(var(--m), 0.12);
    box-shadow: inset 0 0 0 1px rgba(var(--m), 0.5);
  }

  .day-mode-button:disabled {
    cursor: default;
    opacity: 0.6;
  }

  .tile-key,
  .row-key {
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--hs-text-2);
  }

  .tile-value {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    font-size: 13px;
    font-weight: 500;
  }

  .tile-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .day-icon {
    flex: none;
    --mdc-icon-size: 16px;
    color: rgb(var(--m));
  }

  .tile-value .chevron {
    flex: none;
    --mdc-icon-size: 18px;
    color: var(--hs-text-2);
    transition: transform 0.2s;
  }

  .day-mode-button[aria-expanded="true"] .chevron {
    transform: rotate(180deg);
    color: rgb(var(--m));
  }

  .next-at {
    flex: none;
    font-size: 12px;
    font-weight: 400;
    color: var(--hs-text-2);
  }

  .day-mode-list {
    position: absolute;
    left: 0;
    right: 0;
    top: calc(100% + 6px);
    margin: 0;
    padding: 4px;
    list-style: none;
    border-radius: 12px;
    background: rgba(18, 26, 36, 0.98);
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.08),
      0 12px 30px rgba(0, 0, 0, 0.5);
    animation: pop 0.15s ease-out;
  }

  .day-mode-option {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 34px;
    padding: 0 10px;
    border-radius: 9px;
    font-size: 13px;
    cursor: pointer;
    --mdc-icon-size: 16px;
  }

  .day-mode-option ha-icon {
    flex: none;
    color: var(--hs-text-2);
  }

  .option-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .day-mode-option .check {
    visibility: hidden;
  }

  .day-mode-option.active {
    background: rgba(255, 255, 255, 0.07);
  }

  .day-mode-option[aria-selected="true"] {
    background: rgba(var(--m), 0.18);
  }

  .day-mode-option[aria-selected="true"].active {
    background: rgba(var(--m), 0.26);
  }

  .day-mode-option[aria-selected="true"] ha-icon {
    visibility: visible;
    color: rgb(var(--m));
  }

  @keyframes pop {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
  }

  /* Collapsed by default: the value is readable without opening anything. */
  .setting {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .setting-head {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    height: 36px;
    padding: 0 10px;
    border: 0;
    border-radius: 11px;
    background: var(--hs-surface);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
    color: var(--hs-text);
    font-size: 12.5px;
    font-weight: 500;
    text-align: left;
    cursor: pointer;
  }

  .setting-head:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.09);
  }

  .setting-head:disabled {
    cursor: default;
  }

  .setting-head:disabled .chevron {
    visibility: hidden;
  }

  .setting-head ha-icon {
    flex-shrink: 0;
    --mdc-icon-size: 17px;
    color: var(--hs-text-2);
  }

  .setting-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .setting-value {
    color: var(--hs-text-2);
  }

  .setting-value.set {
    color: rgb(var(--m));
  }

  .setting .chevron {
    transition: transform 0.15s ease;
  }

  .setting.open .chevron {
    transform: rotate(180deg);
  }

  .setting-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px;
    border-radius: 11px;
    background: rgba(0, 0, 0, 0.22);
    animation: fadeIn 0.15s ease;
  }

  .stepper {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
  }

  .stepper button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.07);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
    color: var(--hs-text);
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
  }

  .stepper button:active:not(:disabled) {
    transform: scale(0.9);
    background: rgba(var(--m), 0.3);
  }

  .stepper button:disabled {
    opacity: 0.35;
    cursor: default;
  }

  .stepper-value {
    min-width: 70px;
    text-align: center;
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .setting-effect {
    margin: 0;
    font-size: 12px;
    line-height: 1.4;
    text-align: center;
    color: var(--hs-text-2);
  }

  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .covers-row {
    display: grid;
    grid-template-columns: auto 1fr;
  }

  .cover-times {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 1fr;
    gap: 6px;
  }

  .cover-time {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 40px;
    padding: 0 8px;
    border: 0;
    border-radius: 11px;
    background: var(--hs-surface);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
    color: var(--hs-text);
    font-size: 14px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }

  /* Roller shutter: amber when it opens, blue when it closes. */
  .cover-icon {
    flex: none;
    width: 24px;
    height: 24px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.6;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .cover-time.open .cover-icon {
    color: #ffa63d;
  }

  .cover-time.close .cover-icon {
    color: #7ea2ff;
  }

  .cover-icon .solid {
    fill: currentColor;
    fill-opacity: 0.55;
  }

  .cover-icon .fill {
    fill: currentColor;
    fill-opacity: 0.3;
    stroke: none;
  }

  .cover-icon .rails {
    stroke-width: 1.2;
    stroke-opacity: 0.5;
  }

  .cover-time.actionable {
    cursor: pointer;
  }

  .cover-time.actionable:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
  }

  .cover-time.actionable:disabled {
    cursor: progress;
  }

  .cover-time.pending {
    animation: cover-pending 0.8s ease-in-out infinite alternate;
  }

  @keyframes cover-pending {
    from {
      opacity: 1;
    }
    to {
      opacity: 0.5;
    }
  }

  .error {
    position: relative;
    padding: 14px;
    color: #ff8a80;
  }

  /* Climate auto start/stop: green when VTherm may stop it, the mode's
     colour while a comfort range keeps it running, grey when not driven. */
  .heat-pumps {
    display: flex;
    flex-direction: column;
    gap: 6px;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.035);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
  }

  .heat-pumps-head {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    height: 36px;
    padding: 0 10px;
    border: 0;
    border-radius: 11px;
    background: var(--hs-surface);
    color: var(--hs-text);
    font-size: 12.5px;
    font-weight: 500;
    text-align: left;
    cursor: pointer;
  }

  .heat-pumps-head:hover {
    background: rgba(255, 255, 255, 0.09);
  }

  .heat-pumps-head ha-icon {
    flex-shrink: 0;
    --mdc-icon-size: 17px;
    color: var(--hs-text-2);
  }

  /* The summary is what changes, so it keeps its width; a long title is the
     part cut short. */
  .heat-pumps-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .heat-pumps-summary {
    flex: none;
    white-space: nowrap;
    color: var(--hs-text-2);
  }

  .heat-pumps-head ha-icon.manual {
    --mdc-icon-size: 15px;
    color: #ffc24d;
  }

  .heat-pumps-head .chevron {
    transition: transform 0.15s ease;
  }

  .heat-pumps.open .heat-pumps-head .chevron {
    transform: rotate(180deg);
  }

  .heat-pump-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 0 8px 8px;
    animation: fadeIn 0.15s ease;
  }

  .heat-pump {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px 10px;
    border: 0;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
    color: var(--hs-text);
    text-align: left;
    cursor: pointer;
    transition: background 0.2s;
  }

  .heat-pump:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.09);
  }

  .heat-pump:disabled {
    cursor: default;
  }

  .heat-pump-icon {
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    --mdc-icon-size: 17px;
  }

  .heat-pump-text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .heat-pump-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
    font-weight: 500;
  }

  .heat-pump-status {
    margin-top: 1px;
    font-size: 11.5px;
    color: var(--hs-text-2);
  }

  .heat-pump-manual {
    color: #ffc24d;
  }

  .heat-pump-tag {
    flex: none;
    display: flex;
    align-items: center;
    gap: 5px;
    height: 22px;
    padding: 0 9px;
    border-radius: 11px;
    font-size: 11.5px;
    font-weight: 500;
    --mdc-icon-size: 13px;
  }

  .heat-pump.auto .heat-pump-icon,
  .heat-pump.auto .heat-pump-tag {
    background: rgba(62, 201, 122, 0.15);
    color: #7fe0aa;
  }

  .heat-pump.auto .heat-pump-tag {
    box-shadow: inset 0 0 0 1px rgba(62, 201, 122, 0.3);
  }

  .heat-pump.comfort .heat-pump-icon,
  .heat-pump.comfort .heat-pump-tag {
    background: rgba(var(--m), 0.16);
    color: rgb(var(--m));
  }

  .heat-pump.comfort .heat-pump-tag {
    box-shadow: inset 0 0 0 1px rgba(var(--m), 0.35);
  }

  .heat-pump.idle .heat-pump-icon,
  .heat-pump.idle .heat-pump-tag {
    background: var(--hs-surface);
    color: var(--hs-text-2);
  }

  /* Alerts only exist while something is wrong; nothing is shown otherwise. */
  .alerts {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 11px;
    border: 0;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 500;
    animation: fadeIn 0.3s ease;
  }

  .chip ha-icon {
    --mdc-icon-size: 15px;
  }

  button.chip {
    cursor: pointer;
  }

  .covers-detail {
    margin: 0;
    font-size: 12px;
    line-height: 1.4;
    color: var(--hs-text);
  }

  .chip--heat {
    background: rgba(239, 83, 80, 0.18);
    box-shadow: inset 0 0 0 1px rgba(239, 83, 80, 0.3);
    color: #ffb4b2;
    animation:
      fadeIn 0.3s ease,
      heat-pulse 2.4s ease-in-out infinite;
  }

  @keyframes heat-pulse {
    50% {
      box-shadow:
        inset 0 0 0 1px rgba(239, 83, 80, 0.5),
        0 0 10px rgba(239, 83, 80, 0.4);
    }
  }

  /* A paused cover is a choice, not a fault: calm colour, no animation. */
  .chip--paused {
    background: var(--hs-surface);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
    color: var(--hs-text);
  }

  .chip--paused ha-icon {
    color: var(--hs-text-2);
  }

  /* Pulses: a cover left up is something to act on tonight, not a steady
     status. */
  .chip--covers {
    background: rgba(255, 184, 64, 0.18);
    box-shadow: inset 0 0 0 1px rgba(255, 184, 64, 0.35);
    color: #ffc24d;
    animation:
      fadeIn 0.3s ease,
      covers-left-open-blink 1.2s ease-in-out infinite;
  }

  @keyframes covers-left-open-blink {
    50% {
      opacity: 0.55;
    }
  }

  .cover-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .cover-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 0 1px var(--hs-ring);
    font-size: 13px;
    font-weight: 500;
  }

  .cover-name {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .cover-status {
    margin-top: 1px;
    font-size: 11.5px;
    font-weight: 400;
    color: var(--hs-text-2);
  }

  .cover-item.paused .cover-status {
    color: #ffc24d;
  }

  .cover-toggle,
  .resume-all {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    height: 30px;
    padding: 0 11px;
    border: 0;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.07);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
    color: var(--hs-text);
    font-size: 12.5px;
    font-weight: 500;
    cursor: pointer;
  }

  .cover-toggle ha-icon {
    --mdc-icon-size: 15px;
  }

  .cover-toggle:hover,
  .resume-all:hover {
    background: rgba(255, 255, 255, 0.12);
  }

  .cover-item.paused .cover-toggle {
    background: rgba(255, 184, 64, 0.18);
    box-shadow: inset 0 0 0 1px rgba(255, 184, 64, 0.35);
    color: #ffc24d;
  }

  .resume-all {
    align-self: center;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(3px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* Schedules: a bar at the foot of the card, and the panel it slides up. */
  .schedules-bar {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    margin: 0;
    padding: 12px 14px;
    border: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.07);
    background: transparent;
    color: var(--hs-text-2);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: left;
    cursor: pointer;
  }

  .schedules-bar:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  .schedules-bar:focus-visible {
    outline-offset: -2px;
  }

  .schedules-bar ha-icon {
    flex-shrink: 0;
    --mdc-icon-size: 17px;
  }

  .schedules-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .schedules-mode {
    font-size: 12.5px;
    color: var(--hs-text);
    text-transform: none;
    letter-spacing: normal;
  }

  /* Anchored to the foot of the card and as tall as its content: the top
     of the card stays in sight while the schedules are shorter than it;
     longer ones scroll inside the panel. */
  .schedules-panel {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    max-height: calc(100% - 24px);
    z-index: 3;
    display: flex;
    flex-direction: column;
    border-top: 1px solid rgba(var(--m), 0.3);
    border-radius: 18px 18px 0 0;
    background: linear-gradient(
      180deg,
      rgba(18, 26, 36, 0.99),
      rgba(10, 15, 22, 0.99)
    );
    box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.4);
    animation: schedules-slide-up 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .schedules-panel .schedules-bar {
    border-top: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  }

  .schedules-body {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 12px 14px 14px;
  }

  @keyframes schedules-slide-up {
    from {
      transform: translateY(100%);
    }
    to {
      transform: translateY(0);
    }
  }

  /* The colours alone still tell the mode, the warning and the state. */
  @media (prefers-reduced-motion: reduce) {
    .glow,
    .badge ha-icon,
    .chip--heat,
    .chip--covers,
    .cover-time.pending,
    .schedules-panel,
    .day-mode-list {
      animation: none !important;
    }
    .particles {
      display: none;
    }
  }
`;
