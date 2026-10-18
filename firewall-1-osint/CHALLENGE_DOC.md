# Firewall 1 - Challenge Documentation (pentest brief)
NPC Inc "NPC Pulse" - OSINT / information-disclosure recon.

Firewall 1 is the **reconnaissance phase** of the engagement. Players do not
exploit code here; they harvest information a company has carelessly exposed,
log in as the insider using what she overshares, and follow her private trail to
the hidden staff portal, which is where **Firewall 2** (exploitation) begins.
No CTF flag strings are used; answers are the real intel.

Every stage's loot is the literal key to the next, so the chain cannot be
short-circuited: **staff ID -> login username; password -> session; codename ->
folder name; removed-posts log -> which "deleted" post is still live (#106);
base64 inside /post/106 -> portal path -> F2's door.**

Solvable with a browser and the offline LLM only. No local tools (exiftool,
terminal) are required: the LLM handles base64, and SVG source is read in the
browser.

---

## Stage 1 - Insider identification
- **Class:** OSINT profiling / correlation of public information.
- **Exposure:** an employee overshares about causing an incident; her staff ID is public on her profile.
- **Recon path:** read feed -> correlate the panicking intern with the "who skipped the auth gate" callout -> she is not in suggestions, so Search -> open profile.
- **Loot:** Staff ID `NPC-2291`.
- **Key to next:** it is her login **username**.
- **Lesson:** individually harmless posts become identifying when correlated.

## Stage 2 - Credential profiling against a known policy
- **Class:** Weak password built from a published policy + personal information; auth hygiene.
- **Exposure:** the **signup page states only the password SHAPE** (two words + # + birth year), not the recipe - and Dani is staff, so her password follows the same shape. Which two words (her pet + her book, with the matcha drink as a decoy) is never disclosed by the system; Theo roasts it out of her in the **comments** on post #120 ("two of your favourite things and the year you were born, you posted all three"). Her values are scattered: the book in a post, the birth year in her birthday post, and the pet's name only in the **comments** on #127 (someone names the cat, she agrees). A legacy "password hint" on the login page leaks only the shape (word word # yyyy) when a valid staff ID is entered with a wrong password. Username enumeration: unknown vs known IDs are rejected differently.
- **Recon path:** read the policy shape -> from the banter work out it is two favourites + year -> recover book/year/pet across posts and comments -> assemble -> log in. The three favourite candidates (cat, book, matcha) give a handful of brute-forceable two-word combos. Decoys: a loud "favourite drink" (matcha) that is NOT in the password, a wrong guess in the comments, kiosk creds, and an expired password.
- **Loot:** password `MochiDune#2004`.
- **Key to next:** it logs you in as Dani (the session).
- **Lesson:** a shared/known policy makes passwords profileable; never build a password from details you post; never disclose password hints; distinct auth errors enable enumeration.

## Stage 3 - Private data disclosure (post-authentication)
- **Class:** Broken access control / sensitive data behind a weak login.
- **Exposure:** once logged in as Dani, her inbox (DMs) reveals the internal migration codename and that she relocated the real notes into a project folder named after it. None of this is public.
- **Recon path:** log in -> Messages -> read the argument with Theo.
- **Loot:** migration codename `SKYLINE`.
- **Key to next:** it is the **project folder name** (`/projects/skyline/`).
- **Lesson:** a login is not a vault; weak auth exposes everything behind it.

## Stage 4 - "Deleted" is not deleted
- **Class:** Broken access control / data remnants (unlisting hides from the UI but the object is still served).
- **Exposure:** `robots.txt` advertises `/projects/`; its index is disabled (no enumeration), but the folder name is known from S3. Inside `/projects/skyline/` is `removed-posts.log` - Dani's panic note. It deliberately does **not** name a post. It only says the trouble is the **attached `.svg` graphic** (the leak is inside the file, not the caption) and that unlisting only hides a post from her profile, so unlisted posts **still open if you type the post number into the URL**. The player has to hunt the posts themselves.
- **Recon path:** robots.txt -> `/projects/` (listing disabled) -> `/projects/skyline/` -> read `removed-posts.log` -> enumerate `/post/<id>`: most removed ids show a plain "post deleted" page, a few troll posts still open live as dead ends, and one (#106) still opens **and still carries the notice graphic** -> that is the one. Theo's DM ("your deleted post still opens... nobody is going to type the number in") reinforces the id-in-the-URL idea without naming it.
- **Loot:** `106` (the still-live post that still has the SVG attachment).
- **Key to next:** that post is where S5 lives.
- **Lesson:** removing a post from a listing is not deletion; the object is still retrievable, and you often have to enumerate to find it. The clue points at the *class* of artifact (the attached file), not the exact object.

## Stage 5 - Sensitive data exposure (Firewall 2 pivot)
- **Class:** Sensitive data exposure; "encoding is not encryption"; authorization-scoped content.
- **Exposure:** `/post/106` carries an **SVG attachment** whose `<metadata>` hides the relocated production portal path, base64-encoded. The attachment (`/post/106/asset.svg`) is served **only to Dani's session**; to anyone else the post shows only the panic caption and no attachment, so the secret cannot leak ahead of the chain. The answer is in the file, not the caption.
- **Recon path:** open `/post/106` as Dani -> save/open the attached SVG -> read its source -> decode the base64 (via the LLM).
- **Loot:** portal path `/internal-portal`. **This unlocks Firewall 2.**
- **Lesson:** base64 is reversible; exported assets carry hidden metadata; and the same object can expose more to a privileged session - fetch it with the right identity.

## Stage 6 - SVG source inspection (bonus, hardest)
- **Class:** Metadata / artifact disclosure in a vector asset.
- **Exposure:** a poster SVG ships with an "export note" containing a base64 setup code in `<metadata>`. Two other posters are decoys (one clean, one with only a troll comment).
- **Recon path:** recognise SVG is text -> save and open source -> find the right poster -> decode the base64.
- **Loot:** setup code `npc-setup-override-7731`.
- **Lesson:** exported assets carry hidden layers/metadata; vector files are code, not flat images.

---

## Deliberate time-sinks (anti-rush design)
- **Troll tools / decode traps:** two base64 decoys (a gym caption, a survey file) that decode to jokes, and a whole decoy exposed directory (`/resources/`) that robots.txt points at but leads nowhere. Lesson: not every tool-use pays off.
- **Decoy credentials:** sticky-note kiosk creds (`NPC-1001`/`Welcome123!`) that log in but to a dead-end account; an expired old password (`sunshine2004`).
- **False loot:** `NPC-0001` and `/employee-dashboard` look right and are rejected by the scoreboard.
- **Troll "removed" pages:** during the S4 hunt, most removed post-ids show a plain "post deleted" page, and a couple of troll posts (e.g. #111) still open live as dead ends with no attachment. Only #106 opens AND still carries the notice graphic.

## Hand-off to Firewall 2
Firewall 1 ends at the discovery of `/internal-portal`. It never reveals how F2
is exploited (no cookies, keys, or admin technique). F1 runs its own signed login
cookie with a server-only key, independent of F2, so F2's cookie trick cannot
skip the F1 login. CTFd gates the F2 challenge behind the Stage 5 answer. Recon
feeds exploitation; the boundaries stay clean.

## Progressive gating
S1 -> S2 -> S3 -> S4 -> S5 -> Firewall 2, enforced as CTFd prerequisites. S6 is
an independent bonus with no dependents.
