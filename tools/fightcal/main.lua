-- One-off helper: spawns skeletons at known world offsets next to the hero and takes screenshots, to learn the world -> screen mapping.
if not gear.auto then return end
local A = gear.auto
gear.task(function()
    if not A.wait_for_menu(gear.config.timeout_menu) then return A.quit(2) end
    if not A.wait_for_game(gear.config.timeout_game) then return A.quit(3) end
    gear.wait(4)
    local hero = gear.world.hero()
    local x, y, layer = hero:position()
    A.write('hero.txt', ('%d %d %d'):format(x, y, layer))
    A.screenshot('cal-0')
    local offsets = {{250, 0}, {0, 250}, {-250, 0}, {0, -250}}
    for i, o in ipairs(offsets) do
        gear.world.spawn(32, x + o[1], y + o[2], {layer = layer})
        gear.wait(1.5)
        A.screenshot('cal-' .. i)
    end
    A.quit(0)
end)
