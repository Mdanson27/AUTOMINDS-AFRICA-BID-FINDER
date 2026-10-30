-- AutoMinds Africa Bid Finder - Neon production schema
-- Firebase remains the identity provider. Neon Data API validates Firebase JWTs.

CREATE TABLE IF NOT EXISTS public.app_users (
  firebase_uid text PRIMARY KEY,
  email text NOT NULL DEFAULT '',
  display_name text NOT NULL DEFAULT '',
  role text NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer','admin')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_preferences (
  owner_uid text PRIMARY KEY REFERENCES public.app_users(firebase_uid) ON DELETE CASCADE,
  scope text NOT NULL DEFAULT 'all' CHECK (scope IN ('all','government','newspapers','development','private')),
  closing_soon_days integer NOT NULL DEFAULT 14 CHECK (closing_soon_days IN (3,7,14,30)),
  default_sort text NOT NULL DEFAULT 'deadline' CHECK (default_sort IN ('deadline','newest','organization')),
  active_only boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_uid text UNIQUE NOT NULL REFERENCES public.app_users(firebase_uid) ON DELETE CASCADE,
  company_name text NOT NULL DEFAULT '',
  trading_name text NOT NULL DEFAULT '',
  registration_number text NOT NULL DEFAULT '',
  tin text NOT NULL DEFAULT '',
  company_type text NOT NULL DEFAULT '',
  industry text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  website text NOT NULL DEFAULT '',
  email text NOT NULL DEFAULT '',
  phone text NOT NULL DEFAULT '',
  address text NOT NULL DEFAULT '',
  district text NOT NULL DEFAULT '',
  country text NOT NULL DEFAULT 'Uganda',
  services text[] NOT NULL DEFAULT '{}',
  keywords text[] NOT NULL DEFAULT '{}',
  coverage text[] NOT NULL DEFAULT '{}',
  preferred_contract_min numeric(18,2) NOT NULL DEFAULT 0,
  preferred_contract_max numeric(18,2) NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'UGX',
  years_experience integer NOT NULL DEFAULT 0 CHECK (years_experience >= 0),
  past_clients text[] NOT NULL DEFAULT '{}',
  reference_notes text NOT NULL DEFAULT '',
  certifications text[] NOT NULL DEFAULT '{}',
  compliance jsonb NOT NULL DEFAULT '{"ursbRegistered":false,"taxClearance":false,"ppdaRegistered":false,"vatRegistered":false}'::jsonb,
  profile_status text NOT NULL DEFAULT 'incomplete' CHECK (profile_status IN ('active','incomplete')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.sources (
  id text PRIMARY KEY,
  name text NOT NULL,
  source_type text NOT NULL DEFAULT 'website',
  source_group text NOT NULL DEFAULT 'other',
  base_url text NOT NULL DEFAULT '',
  health text NOT NULL DEFAULT 'planned',
  enabled boolean NOT NULL DEFAULT true,
  last_successful_crawl_at timestamptz,
  last_attempted_crawl_at timestamptz,
  records_found integer NOT NULL DEFAULT 0,
  records_created integer NOT NULL DEFAULT 0,
  records_updated integer NOT NULL DEFAULT 0,
  records_unchanged integer NOT NULL DEFAULT 0,
  last_error text NOT NULL DEFAULT '',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.organizations (
  id text PRIMARY KEY,
  name text NOT NULL,
  organization_type text NOT NULL DEFAULT '',
  website text NOT NULL DEFAULT '',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.bids (
  id text PRIMARY KEY,
  title text NOT NULL,
  organization text NOT NULL DEFAULT '',
  organization_id text REFERENCES public.organizations(id) ON DELETE SET NULL,
  reference_number text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  category text NOT NULL DEFAULT '',
  procurement_type text NOT NULL DEFAULT '',
  procurement_method text NOT NULL DEFAULT '',
  source_stage text NOT NULL DEFAULT '',
  canonical_source text NOT NULL DEFAULT '',
  canonical_source_url text NOT NULL DEFAULT '',
  canonical_identity text NOT NULL DEFAULT '',
  title_specificity text NOT NULL DEFAULT '',
  title_source text NOT NULL DEFAULT '',
  display_eligible boolean NOT NULL DEFAULT true,
  opportunity_type text NOT NULL DEFAULT 'tender',
  notice_type text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'open',
  is_open boolean NOT NULL DEFAULT true,
  fingerprint text NOT NULL DEFAULT '',
  published_at timestamptz,
  deadline_at timestamptz NOT NULL,
  opening_at timestamptz,
  application_url text NOT NULL DEFAULT '',
  first_seen_at timestamptz,
  first_detected_at timestamptz,
  last_seen_at timestamptz,
  last_verified_at timestamptz,
  verification_status text NOT NULL DEFAULT '',
  verification_note text NOT NULL DEFAULT '',
  retention_status text NOT NULL DEFAULT '',
  retained_from_previous_snapshot boolean NOT NULL DEFAULT false,
  deadline_changed boolean NOT NULL DEFAULT false,
  deadline_changed_at timestamptz,
  documents jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  intelligence jsonb,
  contacts jsonb NOT NULL DEFAULT '[]'::jsonb,
  bidders jsonb NOT NULL DEFAULT '[]'::jsonb,
  bids_received integer,
  opening_participants jsonb NOT NULL DEFAULT '[]'::jsonb,
  opening_committee jsonb NOT NULL DEFAULT '[]'::jsonb,
  amendments jsonb NOT NULL DEFAULT '[]'::jsonb,
  lifecycle_events jsonb NOT NULL DEFAULT '[]'::jsonb,
  best_evaluated_bidder text NOT NULL DEFAULT '',
  contract_amount text NOT NULL DEFAULT '',
  contract_currency text NOT NULL DEFAULT '',
  phase4_enriched boolean NOT NULL DEFAULT false,
  raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bids_deadline_idx ON public.bids(deadline_at);
CREATE INDEX IF NOT EXISTS bids_status_deadline_idx ON public.bids(status, deadline_at);
CREATE INDEX IF NOT EXISTS bids_org_idx ON public.bids(organization);
CREATE INDEX IF NOT EXISTS bids_reference_idx ON public.bids(reference_number);
CREATE INDEX IF NOT EXISTS bids_published_idx ON public.bids(published_at DESC);

CREATE TABLE IF NOT EXISTS public.bid_sources (
  bid_id text NOT NULL REFERENCES public.bids(id) ON DELETE CASCADE,
  source_id text NOT NULL REFERENCES public.sources(id) ON DELETE CASCADE,
  source_name text NOT NULL DEFAULT '',
  source_url text NOT NULL DEFAULT '',
  source_reference text NOT NULL DEFAULT '',
  detected_at timestamptz,
  deadline_at timestamptz,
  published_at timestamptz,
  verified boolean NOT NULL DEFAULT false,
  raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (bid_id, source_id, source_url)
);

CREATE TABLE IF NOT EXISTS public.bid_changes (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  bid_id text NOT NULL REFERENCES public.bids(id) ON DELETE CASCADE,
  change_type text NOT NULL,
  old_value jsonb,
  new_value jsonb,
  detected_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bid_changes_bid_idx ON public.bid_changes(bid_id, detected_at DESC);

CREATE TABLE IF NOT EXISTS public.crawl_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text REFERENCES public.sources(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'running',
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  records_found integer NOT NULL DEFAULT 0,
  records_created integer NOT NULL DEFAULT 0,
  records_updated integer NOT NULL DEFAULT 0,
  error text NOT NULL DEFAULT '',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.procurement_plans (
  id text PRIMARY KEY,
  name text NOT NULL DEFAULT 'Procurement plan',
  organization text NOT NULL DEFAULT '',
  financial_year text NOT NULL DEFAULT '',
  total_estimated_amount_ugx text NOT NULL DEFAULT '',
  source_url text NOT NULL DEFAULT '',
  pdf_url text NOT NULL DEFAULT '',
  excel_url text NOT NULL DEFAULT '',
  collected_at timestamptz,
  items jsonb NOT NULL DEFAULT '[]'::jsonb,
  raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.grants (
  id text PRIMARY KEY,
  title text NOT NULL,
  organization text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  category text NOT NULL DEFAULT '',
  published_at timestamptz,
  deadline_at timestamptz NOT NULL,
  source_id text REFERENCES public.sources(id) ON DELETE SET NULL,
  source_url text NOT NULL DEFAULT '',
  display_eligible boolean NOT NULL DEFAULT true,
  raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS grants_deadline_idx ON public.grants(deadline_at);

CREATE TABLE IF NOT EXISTS public.saved_bids (
  owner_uid text NOT NULL REFERENCES public.app_users(firebase_uid) ON DELETE CASCADE,
  bid_id text NOT NULL,
  stage text NOT NULL DEFAULT 'watching',
  notes text NOT NULL DEFAULT '',
  snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  saved_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (owner_uid, bid_id)
);

CREATE TABLE IF NOT EXISTS public.saved_searches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_uid text NOT NULL REFERENCES public.app_users(firebase_uid) ON DELETE CASCADE,
  name text NOT NULL,
  query jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_uid text NOT NULL REFERENCES public.app_users(firebase_uid) ON DELETE CASCADE,
  notification_type text NOT NULL DEFAULT 'general',
  title text NOT NULL,
  body text NOT NULL DEFAULT '',
  bid_id text,
  read_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS notifications_owner_created_idx ON public.notifications(owner_uid, created_at DESC);

CREATE TABLE IF NOT EXISTS public.bid_match_scores (
  owner_uid text NOT NULL REFERENCES public.app_users(firebase_uid) ON DELETE CASCADE,
  bid_id text NOT NULL REFERENCES public.bids(id) ON DELETE CASCADE,
  score integer NOT NULL CHECK (score BETWEEN 0 AND 100),
  reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
  risks jsonb NOT NULL DEFAULT '[]'::jsonb,
  calculated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (owner_uid, bid_id)
);

CREATE OR REPLACE FUNCTION public.is_bidfinder_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.app_users
    WHERE firebase_uid = auth.user_id() AND role = 'admin'
  );
$$;
REVOKE ALL ON FUNCTION public.is_bidfinder_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_bidfinder_admin() TO authenticated;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT ON public.app_users TO authenticated;
GRANT UPDATE (email, display_name, updated_at) ON public.app_users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_preferences, public.companies, public.saved_bids, public.saved_searches TO authenticated;
GRANT SELECT, UPDATE, INSERT ON public.notifications TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.bids, public.bid_sources, public.bid_changes, public.sources, public.organizations, public.procurement_plans, public.grants, public.crawl_runs, public.bid_match_scores TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

ALTER TABLE public.app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_bids ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bids ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bid_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bid_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procurement_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bid_match_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY app_users_select_own ON public.app_users FOR SELECT TO authenticated USING (auth.user_id() = firebase_uid);
CREATE POLICY app_users_insert_own ON public.app_users FOR INSERT TO authenticated WITH CHECK (auth.user_id() = firebase_uid AND role = 'viewer');
CREATE POLICY app_users_update_own ON public.app_users FOR UPDATE TO authenticated USING (auth.user_id() = firebase_uid) WITH CHECK (auth.user_id() = firebase_uid);
CREATE POLICY user_preferences_own ON public.user_preferences FOR ALL TO authenticated USING (auth.user_id() = owner_uid) WITH CHECK (auth.user_id() = owner_uid);
CREATE POLICY companies_own ON public.companies FOR ALL TO authenticated USING (auth.user_id() = owner_uid) WITH CHECK (auth.user_id() = owner_uid);
CREATE POLICY saved_bids_own ON public.saved_bids FOR ALL TO authenticated USING (auth.user_id() = owner_uid) WITH CHECK (auth.user_id() = owner_uid);
CREATE POLICY saved_searches_own ON public.saved_searches FOR ALL TO authenticated USING (auth.user_id() = owner_uid) WITH CHECK (auth.user_id() = owner_uid);
CREATE POLICY notifications_own_read ON public.notifications FOR SELECT TO authenticated USING (auth.user_id() = owner_uid);
CREATE POLICY notifications_own_update ON public.notifications FOR UPDATE TO authenticated USING (auth.user_id() = owner_uid) WITH CHECK (auth.user_id() = owner_uid);

CREATE POLICY bids_live_read ON public.bids FOR SELECT TO authenticated USING (display_eligible AND is_open AND status NOT IN ('closed','evaluation','awarded','cancelled') AND deadline_at > now());
CREATE POLICY bid_sources_live_read ON public.bid_sources FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.bids b WHERE b.id = bid_id));
CREATE POLICY bid_changes_live_read ON public.bid_changes FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.bids b WHERE b.id = bid_id));
CREATE POLICY sources_read ON public.sources FOR SELECT TO authenticated USING (true);
CREATE POLICY organizations_read ON public.organizations FOR SELECT TO authenticated USING (true);
CREATE POLICY procurement_plans_read ON public.procurement_plans FOR SELECT TO authenticated USING (true);
CREATE POLICY grants_live_read ON public.grants FOR SELECT TO authenticated USING (display_eligible AND deadline_at > now());
CREATE POLICY crawl_runs_read ON public.crawl_runs FOR SELECT TO authenticated USING (true);
CREATE POLICY match_scores_own_read ON public.bid_match_scores FOR SELECT TO authenticated USING (auth.user_id() = owner_uid);

CREATE POLICY collector_bids_write ON public.bids FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_bid_sources_write ON public.bid_sources FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_bid_changes_write ON public.bid_changes FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_sources_write ON public.sources FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_organizations_write ON public.organizations FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_plans_write ON public.procurement_plans FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_grants_write ON public.grants FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_crawl_runs_write ON public.crawl_runs FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_match_scores_write ON public.bid_match_scores FOR ALL TO authenticated USING (auth.user_id() = 'bidfinder-collector') WITH CHECK (auth.user_id() = 'bidfinder-collector');
CREATE POLICY collector_notifications_write ON public.notifications FOR INSERT TO authenticated WITH CHECK (auth.user_id() = 'bidfinder-collector');

CREATE POLICY admin_bids_write ON public.bids FOR ALL TO authenticated USING (public.is_bidfinder_admin()) WITH CHECK (public.is_bidfinder_admin());
CREATE POLICY admin_bid_sources_write ON public.bid_sources FOR ALL TO authenticated USING (public.is_bidfinder_admin()) WITH CHECK (public.is_bidfinder_admin());
CREATE POLICY admin_sources_write ON public.sources FOR ALL TO authenticated USING (public.is_bidfinder_admin()) WITH CHECK (public.is_bidfinder_admin());
