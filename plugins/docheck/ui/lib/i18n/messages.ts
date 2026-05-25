import it from "@/messages/it.json";
import en from "@/messages/en.json";
import fr from "@/messages/fr.json";
import type { Locale } from "./config";

export type Messages = typeof it;

export const MESSAGES: Record<Locale, Messages> = {
  it,
  en: en as Messages,
  fr: fr as Messages,
};
