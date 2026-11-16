---@type GearModManifest
return {
    id = 'reborn',
    name = 'Sacred ReBorn HD',
    version = '0.1.0',
    author = 'Re-creation for Sacred Gear; ReBorn by the Sacred ReBorn Overlookers group',
    description = "Sacred ReBorn HD 4.6 on the plain game: the Overlookers' balance around damage and resistance types (new numbers for heroes, skills, items, bosses and enemies, level 1 to 216 in about 30 hours), their fixes and the quick cast. Open the mod's page here and press Changes to read what it changes.",
    -- gear.auto: only when the game runs with -gear-auto (the self test below).
    automation = true,
    config = {
        abilities = true,       -- apply ReBorn's ability table values (abilities_edits.json)
        timeout_menu = 120,     -- self test: seconds to wait for the main menu
        timeout_game = 180,     -- self test: seconds to wait for the game after loading
        fight = 0,              -- self test: spawn wolves next to the hero and play on this many seconds (the hit code runs)
        idle = 0,               -- self test: seconds to play on (idle in the world) before the checks end
        changes_shot = false,   -- self test: open the Changes screen and take pictures of it
        slotkeys = false,       -- self test: press the skill slot digit keys and count the slot hook's calls
        quit = true,            -- self test: end the game when done
    },
}
