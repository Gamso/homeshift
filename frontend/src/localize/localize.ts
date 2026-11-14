import en from './en.json';
import fr from './fr.json';

type Dict = Record<string, any>;

const languages: Record<string, Dict> = {
  en,
  fr
};

function get(hass: any): string {
  const code = hass?.locale?.language || hass?.language || 'en';
  const short = String(code).split('-')[0];
  return languages[code] ? code : languages[short] ? short : 'en';
}

function resolveKey(obj: Dict, path: string): any {
  return path.split('.').reduce((acc: any, k: string) => (acc && acc[k] != null ? acc[k] : undefined), obj);
}

/**
 * Translates `key` into the Home Assistant user's language.
 *
 * Lookup order: user's language, then English, then `fallback`, then the
 * key itself (so a missing translation stays visible during development).
 */
export function localize(
  hass: any,
  key: string,
  params?: Record<string, string>,
  fallback?: string,
): string {
  const lang = get(hass);
  let text = (resolveKey(languages[lang], key) ??
    resolveKey(languages.en, key) ??
    fallback) as string | undefined;
  if (text == null) return key;
  if (params) {
    // Every occurrence, and the value as is: String.replace would read "$&"
    // or "$'" in it (a cover or an error message) as replacement patterns.
    Object.entries(params).forEach(
      ([k, v]) => (text = (text as string).split(`{${k}}`).join(String(v))),
    );
  }
  return text as string;
}
