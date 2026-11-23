-- Log each voice id the dialogue system requests (US EXE: s16 at 0x800A6430, set by func_8001ACF0 case 3),
-- with a screenshot. Polls once per frame, so no debugger is needed.
local mem = require("ffi").cast("uint8_t*", PCSX.getMemPtr())
local last = -1
L.on_frame(function(n)
  local id = mem[0xA6430] + mem[0xA6431] * 256
  if id ~= last then
    last = id
    if bit.band(id, 0xC000) == 0x4000 then
      L.log(string.format("f%d voice %04X bank %d", n, id, bit.band(bit.rshift(id, 9), 31)))
      L.shot(string.format("voice_f%06d_%04X", n, id))
    end
  end
end)
