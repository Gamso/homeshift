import { ENTITY_FIELDS, EntityConfigKey } from "./types";

/** Platform name of the HomeShift integration in the entity registry. */
const PLATFORM = "homeshift";

/** The registry key of an entity option: the suffix of its default id. */
function translationKey(defaultId: string): string {
  return defaultId.split(".")[1]?.replace(/^homeshift_/, "") ?? "";
}

/**
 * The entities of the HomeShift integration, found in the entity registry by
 * their translation key. Unlike the default ids they follow an entity that was
 * renamed, or created before the ids were pinned to English.
 */
export function discoverEntities(
  hass: any,
): Partial<Record<EntityConfigKey, string>> {
  const found: Partial<Record<EntityConfigKey, string>> = {};
  const registry = Object.values(hass?.entities ?? {}) as any[];
  for (const field of ENTITY_FIELDS) {
    const key = translationKey(field.default);
    if (!key) continue;
    const match = registry.find(
      (entry) => entry.platform === PLATFORM && entry.translation_key === key,
    );
    if (match) found[field.key] = match.entity_id;
  }
  return found;
}
