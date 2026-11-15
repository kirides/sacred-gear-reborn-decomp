-- One-off helper of the ReBorn port: writes GearAutomation\<instance>\abilities_dump.json, every ability of the exe's two
-- tables with its text names (T1 name_text through gear.text.get, and the u16/u32 words at +2..+0x3C of T2 tried as text
-- ids), all fields by name. Run it with:  Sacred.exe -gear-auto -gear-load=1 -gear-mods=abilitydump -gear-instance=dump
if not gear.auto then return end
local A = gear.auto
gear.task(function()
    if not A.wait_for_menu(gear.config.timeout_menu) then return A.quit(2) end
    if not A.wait_for_game(gear.config.timeout_game) then return A.quit(3) end
    gear.wait(3)
    local abilities = gear.data.abilities
    local out = {}
    for _, id in ipairs(abilities:ids()) do
        local a = abilities[id]
        local entry = {id = id, table = a.table}
        for _, f in ipairs(abilities:fields(id)) do entry[f.name] = a[f.name] end
        -- which fields are text ids? try every integer field value as one
        local texts = {}
        for _, f in ipairs(abilities:fields(id)) do
            local v = a[f.name]
            if f.name ~= 'id' and f.kind ~= 'f32' and v and v > 0 then
                local t = gear.text.get(v)
                if t and t ~= '' then texts[f.name] = t:sub(1, 60) end
            end
        end
        entry.texts = texts
        out[#out + 1] = entry
    end
    A.write('abilities_dump.json', gear.json.encode(out))
    print(('dumped %d abilities'):format(#out))
    A.quit(0)
end)
