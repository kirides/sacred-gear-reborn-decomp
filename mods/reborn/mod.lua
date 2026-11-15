---@type GearModManifest
return {
    id = 'reborn',
    name = 'Sacred ReBorn',
    version = '0.1.0',
    -- gear.auto: only when the game runs with -gear-auto (the self test below).
    automation = true,
    config = {
        abilities = true,       -- apply ReBorn's ability table values (abilities_edits.json)
        timeout_menu = 120,     -- self test: seconds to wait for the main menu
        timeout_game = 180,     -- self test: seconds to wait for the game after loading
        fight = 0,              -- self test: spawn wolves next to the hero and play on this many seconds (the hit code runs)
        idle = 0,               -- self test: seconds to play on (idle in the world) before the checks end
        quit = true,            -- self test: end the game when done
    },
}
