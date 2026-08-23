import { createClient } from "@supabase/supabase-js";

// The shell only exposes the publishable key. The secret key is never part of
// this bundle or any browser-facing configuration.
globalThis.OryxenAISupabaseClient = { createClient };
