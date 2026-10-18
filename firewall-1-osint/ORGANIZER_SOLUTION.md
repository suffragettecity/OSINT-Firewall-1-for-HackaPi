# Firewall 1 - ORGANIZERS ONLY - Loot & Full Solve
Keep OFF the player network and out of the Go-Bag. Not needed at runtime.

Base (dev): http://127.0.0.1:5000 (replace with the event host/port).

## Getting in
The site is **gated**: players first create an intern account at `/signup`
(assigned `INT-xxxx`) and must set a password that follows the **company policy
shape** shown on that page - *two words + # + 4-digit birth year* (example
`BingoNarnia#1998`). The page shows only the shape, NOT the categories; Dani's
password follows the same shape, and the "which two words" is roasted out of her
in the comments on post #120.
Interns can browse the feed/profiles/comments but cannot open Dani's inbox, the
SKYLINE folder, or the gated attachment - for those you must log in **as Dani**.

## Loot to load into CTFd (defaults; rotate via .env)
| Stage | Submit string | Technique | Gate |
|---|---|---|---|
| S1 | `NPC-2291` | profiling | unlocks S2 |
| S2 | `MochiDune#2004` | credential profiling (policy password) | unlocks S3 |
| S3 | `SKYLINE` | private-data disclosure (login) | unlocks S4 |
| S4 | `106` | the "deleted" post still live (removed-posts.log) | unlocks S5 |
| S5 | `/internal-portal` | data exposure (base64 in a gated SVG) | **unlocks Firewall 2** |
| S6 | `npc-setup-override-7731` | SVG metadata (1 of 7 posters) | bonus, no gate |

Set CTFd answer matching to **case-insensitive** (the login accepts any case on
the letters but needs the `#` and digits exact). S5 opens the F2 challenge card
(set F2's prerequisite to S5). S6 has no dependents.

## Decoys the scoreboard must REJECT (do not add these as accepted answers)
- `NPC-0001` (CEO post #101) - fake staff ID.
- `/employee-dashboard` (Theo post #116, repeated in a comment; also a S5 SVG decoy) - fake portal path.
- `NPC-1001` / `Welcome123!` (Omar post #119) - real creds, dead-end kiosk account.
- `sunshine2004` (Dani post #117) - her old password, expired.
- `Mochi123` (a comment guess under #120) - a wrong password.
- **matcha** - loudly her "favourite drink" (post #126) but NOT in the password; the policy says *book*, not drink.

### S5 SVG manifest decoys (post 106's attachment)
The attached SVG is a brand-kit export with SIX base64 "hashes" buried mid-line
(a header comment, three identical `<npc:asset-ref>` entries, a cache-key note,
and a gradient `data-seed`). They are unlabelled and carry identical attributes,
so the only way to pick the real one is to decode each and submit. Exactly one
decodes to the real portal path `/internal-portal` (submit value for S5). The
other five are rejects:
- `/client-portal-old`
- `/legacy-sso-portal`
- `/employee-dashboard` (same string as Theo's decoy above)
- `portal-stg.npc.internal`
- `/portal-admin-v2`

## Full solve
**S1 - profiling.** Dani (@d.parkar) is not in "Who to follow". Posts #104/#107/#108 point at the panicking intern. Search "portal"/"intern" -> her profile -> Staff ID `NPC-2291`. This is her login username.

**S2 - policy password.** The signup page states only the shape: *two words + # + birth year*. The comments on post #120 reveal the recipe (Theo: "two of your favourite things and the year you were born, you posted all three"). Recover Dani's three values:
- **pet = Mochi** - confirmed in the **comments** on post #127 (someone asks "isn't that Mochi?", she agrees). Not in any post body.
- **book = Dune** - her post #125 ("re-reading Dune for the fifth time").
- **year = 2004** - post #123 ("turned 22"; 2026 - 22 = 2004).
- Assemble per policy: `MochiDune#2004`. Login is case-insensitive on letters; `#` and digits exact.
- Confirmation: entering `NPC-2291` with a wrong password leaks only the **shape** (`word word # yyyy`) on the login page (valid-ID-only), never the words.
- Rabbit holes: **matcha** (her loud "favourite drink", not used), `Mochi123` (a comment guess), `sunshine2004` (expired), the kiosk creds.

**S3 - private data (login as Dani).** `/messages` is a **conversation list** of ~6 chats (dad jokes, a friend's life advice, IT, Sam, Mira, and Theo). Only the **Theo** thread reveals the migration codename `SKYLINE` and that the notes went into "the project folder, named after the migration". You have to open the threads to find it; public pages never contain `SKYLINE`.

**S4 - the "deleted" post that still opens.** `/robots.txt` disallows `/projects/`; the `/projects/` listing is disabled (you need the codename). `/projects/skyline/` (Dani only) holds `removed-posts.log`. The note deliberately **does not name a post** - it only says the leak is inside the **attached `.svg` graphic** (not the caption) and that unlisting only hides a post from the profile, so unlisted posts **still open by direct URL**. The player then enumerates `/post/<id>`: most removed ids show a plain "post deleted" page, a couple of troll posts (e.g. #111) still open as live dead ends, and **#106** still opens *and* still carries the notice graphic - that is the one. S4 loot = **`106`** (found by the hunt; Theo's DM "nobody is going to type the number in" is the nudge).

**S5 - data exposure (F2 pivot).** Open `/post/106` as Dani. It carries an **SVG attachment** (`notice.svg`). The portal path is hidden in that SVG's `<metadata>`, base64:
```
echo 'L2ludGVybmFsLXBvcnRhbA==' | base64 -d      # -> /internal-portal
```
The attachment is served **only to Dani** (`/post/106/asset.svg` -> 403 for anyone else), so non-Dani visitors see only the panic caption and the path cannot leak ahead of the chain. Submitting `/internal-portal` unlocks F2.

**S6 (bonus) - SVG metadata.** Mira posts **7** posters (five in #115 "can't decide", two more in #133). Save each and read source; only **one** (`poster-3.svg` by default, env-rotatable via `POSTER_REAL`) has an `<metadata>` token:
```
echo '<token from the one real poster>' | base64 -d   # -> npc-setup-override-7731
```
The other six are decoys (some with troll comments). Dani #114 is the in-story pointer.

## Troll decodes (reassurance for NPCs)
- gym caption (#112) base64 -> "nice try detective, this is just my gym selfie caption...".
- `/resources/survey.txt` base64 -> "Q3 all-hands team-building survey (link expired...)".
- `/resources/` itself is a real exposed dir (robots points at it) but a dead end: press boilerplate + the joke survey, nothing that advances the chain.

## Security boundary with F2 (stays clean)
F1 ends at the discovery of `/internal-portal`. It never reveals F2's technique
(no cookies, keys, or admin trick). F1 runs its OWN signed login cookie with a
**server-only** key, so the F2 cookie-forging trick cannot be used to skip the F1
login, and F1 teaches nothing about F2's key. CTFd gates the F2 card behind S5.

## Verify after any rotation
```
cd firewall1 && python -m pytest -q      # 37 tests: gate/signup, all stages, trolls, negatives
```
