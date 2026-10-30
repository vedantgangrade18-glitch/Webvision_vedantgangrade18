// Shapes of the Karu API responses used by the web app (generated OpenAPI types live in packages/api-types).

export type VerificationStatus = "none" | "checking" | "verified" | "not_verified" | "revoked";
export type PassportState = "unverified" | "verified" | "suspended";

export interface ImageSet {
  id: string;
  thumb: string | null;
  card: string | null;
  large: string | null;
  square: string | null;
  jpg: string | null;
  width?: number | null;
  height?: number | null;
  ai?: boolean;
}

export interface Stock {
  state: "in" | "low" | "out";
  count: number;
}

export interface Card {
  id: string;
  code: string;
  title: string;
  price_inr: number | null;
  image: ImageSet | null;
  verification: VerificationStatus;
  stock: Stock;
  maker: { name: string; handle: string | null; place: string; passport_state: PassportState };
  rating: number | null;
  rating_count: number;
  returnable: boolean;
  wishlisted: boolean;
}

export interface Maker {
  id: string;
  handle: string;
  name: string;
  photo_url: string | null;
  crafts: string[];
  years_of_practice: number | null;
  place: string;
  district: string | null;
  state: string | null;
  languages: string[];
  story: string;
  story_lang: string;
  story_translated: boolean;
  voice_url: string | null;
  passport: { code: string | null; state: PassportState; member_since: string };
  stats?: { verified_products: number; reviews: number; rating: number | null; followers: number };
  following?: boolean;
  under_review?: boolean;
}

export interface ProofCheck {
  key: "handmade_look" | "maker_record" | "making_video";
  state: "passed" | "not_passed" | "new_maker" | "missing" | "pending";
}

export interface Proof {
  status: VerificationStatus;
  checks: ProofCheck[];
  making_video: { url: string; duration_s: number | null; poster: string | null } | null;
  registry: { kind: "pehchan" | "gi"; date: string; detail?: string }[];
  photos_original: boolean | null;
  verified_on: string | null;
  revoked_on: string | null;
}

export interface Localized {
  text: string;
  lang: string;
  translated: boolean;
  source_lang: string;
  original: string | null;
}

export interface Product {
  id: string;
  code: string;
  status: string;
  title: Localized;
  description: Localized;
  price_inr: number | null;
  gallery: (ImageSet & { is_primary: boolean; enhanced: boolean })[];
  stock: Stock;
  returnable: boolean;
  return_window_days: number;
  attributes: Record<string, unknown>;
  tags: string[];
  category: { slug: string; name: string } | null;
  craft: { slug: string; name: string; gi_tag: boolean } | null;
  verification: Proof;
  maker: Maker;
  maker_suspended: boolean;
  reviews: { count: number; avg: number | null };
  wishlisted: boolean;
  share_url: string;
  published_at: string | null;
}

export interface KaruIdPage {
  code: string;
  status: string;
  verdict: "verified" | "not_verified" | "checking" | "revoked";
  verified_label: string;
  piece: {
    title: string;
    title_lang: string;
    code: string;
    craft: string | null;
    craft_slug: string | null;
    region: string;
    image: ImageSet | null;
    listing_status: string;
    available: boolean;
    price_inr: number | null;
  };
  maker: Maker | { under_review: true };
  proof: Proof;
  journey: { event: string; date: string; city?: string | null; by_viewer?: boolean }[];
  sold: boolean;
  sold_on: string | null;
  owned_by_viewer: boolean;
  market_context: { low: string; high: string } | null;
}

export interface Me {
  id: string;
  display_name: string | null;
  locale: string;
  roles: string[];
  phone_masked: string | null;
  email: string | null;
  is_artisan: boolean;
  has_artisan_profile: boolean;
  is_staff: boolean;
  totp_enabled: boolean;
  voice_prompts: boolean;
  notification_prefs: Record<string, boolean>;
  amr?: string[];
}

export interface Job {
  id: string;
  type: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  step: string | null;
  steps: { at: string; step: string }[];
  error: string | null;
  result: Record<string, unknown>;
}

export interface PriceAdvice {
  status: string;
  basis: "handmade" | "replica";
  position: "below" | "in_range" | "above" | "unknown";
  price_inr: number | null;
  suggested_inr: number | null;
  handmade: { p25: number; median: number; p75: number; samples: number } | null;
  replica: { p25: number; median: number; p75: number; samples: number } | null;
  message: string;
  compare_message: string | null;
  sources: { site: string; title: string; price_inr: number; url: string }[];
  updated_at: string | null;
  provider: string | null;
  accepted: boolean;
}

export interface PublicConfig {
  providers: Record<string, string>;
  razorpay_key_id: string | null;
  google_client_id: string | null;
  flags: Record<string, boolean>;
  limits: { regenerate_per_listing_per_day: number; voice_note_max_s: number; photos_max: number };
  commerce: Record<string, number | number[]>;
  env: string;
}
