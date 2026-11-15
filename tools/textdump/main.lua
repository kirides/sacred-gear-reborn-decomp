-- One-off helper: writes GearAutomation\<instance>\texts.json, {id = text} for every text id 1..last that gear.text.get knows.
if not gear.auto then return end
local A = gear.auto
gear.task(function()
    if not A.wait_for_menu(gear.config.timeout_menu) then return A.quit(2) end
    local out, n = {}, 0
    for id = 1, gear.config.last do
        local t = gear.text.get(id)
        if t and t ~= '' then out[tostring(id)] = t; n = n + 1 end
    end
    A.write('texts.json', gear.json.encode(out))
    print(('dumped %d texts'):format(n))
    A.quit(0)
end)
