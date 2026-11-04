import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";
import { localize } from "../localize/localize";
import { ENTITY_FIELDS, EntityConfigKey, HomeShiftCardConfig } from "../types";

class HomeShiftCardEditor extends LitElement {
  @property({ attribute: false }) public hass!: any;
  @state() private _config!: HomeShiftCardConfig;

  public setConfig(config: HomeShiftCardConfig): void {
    this._config = config;
  }

  private _onNameChanged(ev: Event) {
    if (!this._config || !this.hass) return;
    const target = ev.target as any;
    const newValue = target.value;
    if (this._config.name === newValue) return;

    const newConfig = { ...this._config, name: newValue };
    this._config = newConfig;
    this._dispatchConfigChanged(newConfig);
  }

  private _onEntityChanged(
    ev: CustomEvent,
    fieldName: EntityConfigKey,
  ) {
    if (!this._config || !this.hass) return;
    const newValue = ev.detail.value;
    if (this._config[fieldName] === newValue) return;

    const newConfig = { ...this._config, [fieldName]: newValue };
    this._config = newConfig;
    this._dispatchConfigChanged(newConfig);
  }

  /** Schedules options: `show_schedules` and `schedule_entities`. */
  private _onScheduleChanged(
    ev: CustomEvent,
    key: "show_schedules" | "schedule_entities",
  ) {
    if (!this._config || !this.hass) return;
    const newConfig = { ...this._config, [key]: ev.detail.value };
    this._config = newConfig;
    this._dispatchConfigChanged(newConfig);
  }

  private _dispatchConfigChanged(newConfig: HomeShiftCardConfig) {
    const event = new CustomEvent("config-changed", {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  protected render() {
    if (!this.hass || !this._config) {
      return html``;
    }

    return html`
      <div class="card-config">
        <ha-textfield
          label="${localize(this.hass, "editor.name")}"
          .value=${this._config.name || ""}
          @input=${this._onNameChanged}
        ></ha-textfield>

        <ha-selector
          .hass=${this.hass}
          .label=${localize(this.hass, "editor.show_schedules")}
          .selector=${{ boolean: {} }}
          .value=${this._config.show_schedules !== false}
          @value-changed=${(e: CustomEvent) =>
            this._onScheduleChanged(e, "show_schedules")}
        ></ha-selector>
        <ha-selector
          .hass=${this.hass}
          .label=${localize(this.hass, "editor.schedule_entities")}
          .selector=${{ entity: { multiple: true } }}
          .value=${this._config.schedule_entities ?? []}
          @value-changed=${(e: CustomEvent) =>
            this._onScheduleChanged(e, "schedule_entities")}
        ></ha-selector>

        <ha-expansion-panel
          outlined
          .header=${localize(this.hass, "editor.entities")}
        >
          <p class="hint">${localize(this.hass, "editor.entities_hint")}</p>
          ${ENTITY_FIELDS.map(
            (field) => html`<ha-entity-picker
              label="${localize(this.hass, `editor.${field.key}`)}"
              .hass=${this.hass}
              .value=${this._config[field.key] || ""}
              .includeDomains=${field.domains}
              @value-changed=${(e: CustomEvent) =>
                this._onEntityChanged(e, field.key)}
              allow-custom-entity
            ></ha-entity-picker>`,
          )}
        </ha-expansion-panel>
      </div>
    `;
  }

  static styles = css`
    .card-config {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 16px 0;
    }

    ha-textfield,
    ha-entity-picker,
    ha-selector {
      width: 100%;
    }

    ha-expansion-panel ha-entity-picker {
      display: block;
      margin-bottom: 16px;
    }

    .hint {
      margin: 8px 0 16px;
      color: var(--secondary-text-color);
      font-size: 13px;
    }
  `;
}

if (!customElements.get("homeshift-card-editor")) {
  customElements.define("homeshift-card-editor", HomeShiftCardEditor);
}

export { HomeShiftCardEditor };
