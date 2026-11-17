# pricer (no model call)

Code-only agent. Logs `define_pricing_criteria`, fetches each founder-entered competitor URL and registers it only if it loads, counts paid one-time prices in one currency, and sets the price to their median when there are at least 3. Fewer than 3 gives `repeat`; an experimental price is possible only through a founder override and is labelled ASSUMPTION.
