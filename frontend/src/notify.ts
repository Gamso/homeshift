import { localize } from "./localize/localize";

/**
 * Shows `key` (with the error as its `{error}` parameter) as the toast Home
 * Assistant uses for its own failed actions.
 */
export function notifyFailure(
  element: HTMLElement,
  hass: any,
  key: string,
  err: unknown,
): void {
  element.dispatchEvent(
    new CustomEvent("hass-notification", {
      detail: {
        message: localize(hass, key, {
          error: (err as any)?.message ?? String(err),
        }),
      },
      bubbles: true,
      composed: true,
    }),
  );
}

/**
 * Calls a service and reports a refusal with `notifyFailure` rather than
 * leaving the promise unhandled. Resolves to whether the call succeeded.
 */
export async function callService(
  element: HTMLElement,
  hass: any,
  failureKey: string,
  domain: string,
  service: string,
  data: Record<string, unknown>,
): Promise<boolean> {
  try {
    await hass.callService(domain, service, data);
    return true;
  } catch (err) {
    notifyFailure(element, hass, failureKey, err);
    return false;
  }
}
