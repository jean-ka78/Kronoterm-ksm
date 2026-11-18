"""Single source of truth for the Kronoterm KSM integration entities.

Run `python3 tools/generate.py` after editing: it rewrites
custom_components/kronoterm_ksm/registers.py and the entity sections of
strings.json / translations/{en,uk,sl}.json.

Addresses are 0-based Modbus addresses (= number in the Kronoterm CNS
documentation minus 1).

Columns: key, address, kind, options, en, uk, sl
kinds:
  temp      S16 x0.1, -50.0 °C and below / above 150 = sensor missing
  temp0     as temp, and 0 = no room thermostat
  troom     S16 x0.1, >= 50.0 = not used (room setpoint)
  u16 / s16 raw integer; options: scale, unit, dc, sc, cat, dis, prec
  u32       two registers, high word first
  cop       COP / SCOP with firmware-dependent scale
  bit       binary sensor from bitmask (options: mask, dc)
  switch    0/1 register (options: cat, dis)
  select    options: map {option_key: raw}, low_byte
  number    options: min, max, step, mul, unit, cat, dis
"""

# fmt: off
SENSORS = [
    # ---------------------------------------------------------------- temperatures
    ("outdoor_temperature", 2102, "temp", {}, "Outdoor temperature", "Зовнішня температура", "Zunanja temperatura"),
    ("flow_temperature", 2103, "temp", {}, "Flow temperature", "Температура подачі", "Temperatura dvižnega voda"),
    ("return_temperature", 2100, "temp", {}, "Return temperature", "Температура зворотки", "Temperatura povratnega voda"),
    ("evaporating_temperature", 2104, "temp", {}, "Evaporating temperature", "Температура випаровування", "Temperatura uparjanja"),
    ("compressor_temperature", 2105, "temp", {}, "Compressor temperature", "Температура компресора", "Temperatura kompresorja"),
    ("dhw_temperature", 2101, "temp", {}, "DHW temperature", "Гаряча вода: температура", "Sanitarna voda: temperatura"),
    ("dhw_current_target", 2023, "temp", {}, "DHW current target", "Гаряча вода: поточна уставка", "Sanitarna voda: trenutna želena"),
    ("buffer_temperature", 2130, "temp", {}, "Buffer tank temperature", "Бак: температура", "Zalogovnik: temperatura"),
    ("buffer_target", 2031, "temp", {}, "Buffer tank target", "Бак: уставка", "Zalogovnik: želena temperatura"),
    ("buffer_calculated", 2033, "temp", {}, "Buffer tank calculated temperature", "Бак: розрахункова температура", "Zalogovnik: izračunana temperatura"),
    ("loop_1_temperature", 2129, "temp", {}, "Loop 1 temperature", "Контур 1: температура", "Krog 1: temperatura"),
    ("loop_1_calculated", 2127, "temp", {}, "Loop 1 calculated flow", "Контур 1: розрахункова подача", "Krog 1: izračunana temperatura"),
    ("loop_1_room_temperature", 2159, "temp0", {}, "Loop 1 room temperature", "Контур 1: кімнатна температура", "Krog 1: sobna temperatura"),
    ("loop_1_room_target", 2190, "troom", {}, "Loop 1 current room target", "Контур 1: поточна кімнатна уставка", "Krog 1: trenutna želena sobna"),
    ("loop_2_temperature", 2109, "temp", {"dis": True}, "Loop 2 temperature", "Контур 2: температура", "Krog 2: temperatura"),
    ("loop_2_calculated", 2187, "temp", {"dis": True}, "Loop 2 calculated flow", "Контур 2: розрахункова подача", "Krog 2: izračunana temperatura"),
    ("loop_2_room_temperature", 2160, "temp0", {"dis": True}, "Loop 2 room temperature", "Контур 2: кімнатна температура", "Krog 2: sobna temperatura"),
    ("loop_2_current_target", 2050, "temp", {"dis": True}, "Loop 2 current target", "Контур 2: поточна уставка", "Krog 2: trenutna želena"),
    ("loop_3_temperature", 2110, "temp", {"dis": True}, "Loop 3 temperature", "Контур 3: температура", "Krog 3: temperatura"),
    ("loop_3_calculated", 2188, "temp", {"dis": True}, "Loop 3 calculated flow", "Контур 3: розрахункова подача", "Krog 3: izračunana temperatura"),
    ("loop_3_room_temperature", 2161, "temp0", {"dis": True}, "Loop 3 room temperature", "Контур 3: кімнатна температура", "Krog 3: sobna temperatura"),
    ("loop_3_current_target", 2060, "temp", {"dis": True}, "Loop 3 current target", "Контур 3: поточна уставка", "Krog 3: trenutna želena"),
    ("loop_4_temperature", 2111, "temp", {"dis": True}, "Loop 4 temperature", "Контур 4: температура", "Krog 4: temperatura"),
    ("loop_4_calculated", 2189, "temp", {"dis": True}, "Loop 4 calculated flow", "Контур 4: розрахункова подача", "Krog 4: izračunana temperatura"),
    ("loop_4_room_temperature", 2162, "temp0", {"dis": True}, "Loop 4 room temperature", "Контур 4: кімнатна температура", "Krog 4: sobna temperatura"),
    ("loop_4_current_target", 2070, "temp", {"dis": True}, "Loop 4 current target", "Контур 4: поточна уставка", "Krog 4: trenutna želena"),
    ("alternative_source_temperature", 2106, "temp", {"dis": True}, "Alternative source temperature", "Альтернативне джерело: температура", "Alternativni vir: temperatura"),
    ("pool_temperature", 2108, "temp", {"dis": True}, "Pool temperature", "Басейн: температура", "Bazen: temperatura"),
    ("pool_current_target", 2079, "temp", {"dis": True}, "Pool current target", "Басейн: поточна уставка", "Bazen: trenutna želena"),
    # ---------------------------------------------------------------- power / performance
    ("electrical_power", 2128, "u16", {"unit": "W", "dc": "power", "sc": "measurement"}, "Electrical power", "Електрична потужність", "Električna moč"),
    ("heating_power", 2328, "u16", {"unit": "W", "dc": "power", "sc": "measurement"}, "Heating power", "Теплова потужність", "Grelna moč"),
    ("load", 2326, "u16", {"unit": "%", "sc": "measurement"}, "Heat pump load", "Навантаження", "Obremenitev TČ"),
    ("cop", 2370, "cop", {}, "COP", "COP", "COP"),
    ("scop", 2371, "cop", {}, "SCOP", "SCOP", "SCOP"),
    ("system_pressure", 2325, "s16", {"scale": 0.1, "unit": "bar", "dc": "pressure", "sc": "measurement", "prec": 1}, "Heating system pressure", "Тиск системи", "Tlak ogrevalnega sistema"),
    ("system_pressure_setting", 2324, "s16", {"scale": 0.1, "unit": "bar", "dc": "pressure", "cat": "diagnostic", "prec": 1}, "Heating system pressure setting", "Тиск системи: налаштування", "Nastavitev tlaka sistema"),
    # ---------------------------------------------------------------- counters
    ("electrical_energy", 2360, "u32", {"unit": "kWh", "dc": "energy", "sc": "total_increasing"}, "Electrical energy", "Електрична енергія", "Električna energija"),
    ("thermal_energy", 2362, "u32", {"unit": "kWh", "dc": "energy", "sc": "total_increasing", "thermal": True}, "Thermal energy", "Теплова енергія", "Toplotna energija"),
    ("groundwater_pumped", 2348, "u32", {"unit": "m³", "dc": "water", "sc": "total_increasing", "dis": True}, "Groundwater pumped", "Перекачана ґрунтова вода", "Prečrpana podtalnica"),
    ("hours_compressor_heating", 2089, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic"}, "Hours compressor heating", "Мотогодини: компресор, опалення", "Ure kompresor ogrevanje"),
    ("hours_compressor_dhw", 2090, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic"}, "Hours compressor DHW", "Мотогодини: компресор, гаряча вода", "Ure kompresor sanitarna voda"),
    ("hours_compressor_cooling", 2088, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic"}, "Hours compressor cooling", "Мотогодини: компресор, охолодження", "Ure kompresor hlajenje"),
    ("hours_main_pump", 2092, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic"}, "Hours main pump", "Мотогодини: головний насос", "Ure glavna obtočna črpalka"),
    ("hours_dhw_pump", 2093, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic"}, "Hours DHW pump", "Мотогодини: насос гарячої води", "Ure sanitarna črpalka"),
    ("hours_backup_heater_1", 2094, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic"}, "Hours backup heater 1", "Мотогодини: нагрівач 1", "Ure dodatno grelo 1"),
    ("hours_backup_heater_2", 2095, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic", "dis": True}, "Hours backup heater 2", "Мотогодини: нагрівач 2", "Ure dodatno grelo 2"),
    ("hours_alternative_source", 2096, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic", "dis": True}, "Hours alternative source", "Мотогодини: альтернативне джерело", "Ure alternativni vir"),
    ("hours_heat_source", 2097, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic", "dis": True}, "Hours heat source", "Мотогодини: джерело тепла", "Ure toplotni vir"),
    ("hours_passive_cooling", 2098, "u16", {"unit": "h", "dc": "duration", "sc": "total_increasing", "cat": "diagnostic", "dis": True}, "Hours passive cooling", "Мотогодини: пасивне охолодження", "Ure pasivno hlajenje"),
]

# Enum sensors: key, address, {raw: state_key}, names, states {state_key: (en, uk, sl)}
SCHEDULE_STATES = {0: "off", 1: "normal", 2: "eco", 3: "comfort"}
SCHEDULE_NAMES = {
    "off": ("Off", "Вимкнено", "Izklop"),
    "normal": ("Normal", "Звичайний", "Normalno"),
    "eco": ("ECO", "ECO", "ECO"),
    "comfort": ("COMFORT", "COMFORT", "COMFORT"),
}
ENUMS = [
    ("current_function", 2000, {0: "heating", 1: "dhw", 2: "cooling", 3: "pool", 4: "disinfection", 5: "standby", 7: "remote_off"}, {},
     ("Current function", "Поточна функція", "Trenutna funkcija"),
     {"heating": ("Heating", "Опалення", "Ogrevanje"), "dhw": ("Hot water", "Гаряча вода", "Sanitarna voda"),
      "cooling": ("Cooling", "Охолодження", "Hlajenje"), "pool": ("Pool heating", "Нагрів басейну", "Ogrevanje bazena"),
      "disinfection": ("Anti-legionella", "Термічна дезінфекція", "Termična dezinfekcija"), "standby": ("Standby", "Очікування", "Mirovanje"),
      "remote_off": ("Remote off", "Дистанційно вимкнено", "Daljinski izklop")}),
    ("error_status", 2005, {0: "none", 1: "warning", 2: "alarm", 3: "notice"}, {},
     ("Error status", "Стан помилок", "Status napake"),
     {"none": ("None", "Немає", "Brez"), "warning": ("Warning", "Попередження", "Opozorilo"),
      "alarm": ("Alarm", "Аварія", "Alarm"), "notice": ("Notice", "Повідомлення", "Obvestilo")}),
    ("season", 2006, {0: "cooling", 1: "heating", 2: "off"}, {},
     ("Season mode", "Сезонний режим", "Režim delovanja"),
     {"cooling": ("Cooling", "Охолодження", "Hlajenje"), "heating": ("Heating", "Опалення", "Ogrevanje"), "off": ("Off", "Вимкнено", "Izklop")}),
    ("operation_program", 2007, {0: "normal", 1: "eco", 2: "comfort", 4: "screed"}, {},
     ("Operation program", "Програма роботи", "Program delovanja"),
     {"normal": ("Normal", "Звичайна", "Normalno"), "eco": ("ECO", "ECO", "ECO"), "comfort": ("COMFORT", "COMFORT", "COMFORT"),
      "screed": ("Screed drying", "Сушіння стяжки", "Sušenje estriha")}),
    ("dhw_schedule", 2026, SCHEDULE_STATES, {}, ("DHW schedule state", "Гаряча вода: за розкладом", "Sanitarna voda: po urniku"), SCHEDULE_NAMES),
    ("buffer_schedule", 2036, SCHEDULE_STATES, {}, ("Buffer schedule state", "Бак: за розкладом", "Zalogovnik: po urniku"), SCHEDULE_NAMES),
    ("loop_1_schedule", 2043, SCHEDULE_STATES, {}, ("Loop 1 schedule state", "Контур 1: за розкладом", "Krog 1: po urniku"), SCHEDULE_NAMES),
    ("loop_2_schedule", 2053, SCHEDULE_STATES, {"dis": True}, ("Loop 2 schedule state", "Контур 2: за розкладом", "Krog 2: po urniku"), SCHEDULE_NAMES),
    ("loop_3_schedule", 2063, SCHEDULE_STATES, {"dis": True}, ("Loop 3 schedule state", "Контур 3: за розкладом", "Krog 3: po urniku"), SCHEDULE_NAMES),
    ("loop_4_schedule", 2073, SCHEDULE_STATES, {"dis": True}, ("Loop 4 schedule state", "Контур 4: за розкладом", "Krog 4: po urniku"), SCHEDULE_NAMES),
    ("pool_schedule", 2082, SCHEDULE_STATES, {"dis": True}, ("Pool schedule state", "Басейн: за розкладом", "Bazen: po urniku"), SCHEDULE_NAMES),
]

BINARY = [
    ("system_running", 1999, 0x1, {"dc": "running"}, "System running", "Система працює", "Sistem deluje"),
    ("compressor", 2317, 0x1, {"dc": "running"}, "Compressor", "Компресор", "Kompresor"),
    ("compressor_2", 2317, 0x2, {"dc": "running", "dis": True}, "Compressor 2", "Компресор 2", "Kompresor 2"),
    ("compressor_protection", 2318, 0x1, {"dc": "problem"}, "Compressor protection", "Компресор: захист", "Kompresor: varovanje"),
    ("compressor_starting", 2318, 0x2, {"dc": "running"}, "Compressor starting", "Компресор: запуск", "Kompresor: zagon"),
    ("defrost", 2010, 0x1, {"dc": "running"}, "Defrost", "Відтавання", "Odtaljevanje"),
    ("main_pump", 2037, 0x1, {"dc": "running"}, "Main circulation pump", "Головний циркуляційний насос", "Glavna obtočna črpalka"),
    ("dhw_pump", 2027, 0x2, {"dc": "running"}, "DHW pump", "Насос гарячої води", "Črpalka sanitarne vode"),
    ("circulation_pump", 2027, 0x1, {"dc": "running"}, "Circulation pump", "Циркуляційний насос", "Cirkulacijska črpalka"),
    ("loop_1_pump", 2044, 0x1, {"dc": "running"}, "Loop 1 pump", "Контур 1: насос", "Krog 1: črpalka"),
    ("loop_1_demand", 2045, 0x1, {"dc": "heat"}, "Loop 1 thermostat demand", "Контур 1: запит термостата", "Krog 1: zahteva termostata"),
    ("loop_2_pump", 2054, 0x1, {"dc": "running", "dis": True}, "Loop 2 pump", "Контур 2: насос", "Krog 2: črpalka"),
    ("loop_2_demand", 2055, 0x1, {"dc": "heat", "dis": True}, "Loop 2 thermostat demand", "Контур 2: запит термостата", "Krog 2: zahteva termostata"),
    ("loop_3_pump", 2064, 0x1, {"dc": "running", "dis": True}, "Loop 3 pump", "Контур 3: насос", "Krog 3: črpalka"),
    ("loop_3_demand", 2065, 0x1, {"dc": "heat", "dis": True}, "Loop 3 thermostat demand", "Контур 3: запит термостата", "Krog 3: zahteva termostata"),
    ("loop_4_pump", 2074, 0x1, {"dc": "running", "dis": True}, "Loop 4 pump", "Контур 4: насос", "Krog 4: črpalka"),
    ("loop_4_demand", 2075, 0x1, {"dc": "heat", "dis": True}, "Loop 4 thermostat demand", "Контур 4: запит термостата", "Krog 4: zahteva termostata"),
    ("pool_pump", 2083, 0x1, {"dc": "running", "dis": True}, "Pool pump", "Басейн: насос", "Bazen: črpalka"),
    ("pool_demand", 2084, 0x1, {"dc": "heat", "dis": True}, "Pool thermostat demand", "Басейн: запит термостата", "Bazen: zahteva termostata"),
    ("additional_source", 2001, 0x1, {"dc": "running"}, "Additional source active", "Додаткове джерело працює", "Dodatni vir deluje"),
    ("frost_protection", 2001, 0x4, {"dc": "running"}, "Frost protection", "Захист від замерзання", "Zaščita pred zmrzaljo"),
    ("pv_signal", 2001, 0x8, {}, "PV signal", "Сигнал PV", "Signal PV"),
    ("silent_mode", 2001, 0x800, {}, "Silent mode", "Тихий режим", "Tihi način"),
    ("boost_mode", 2001, 0x1000, {}, "Boost mode", "Режим Boost", "Način Boost"),
    ("reserve_source", 2002, 0x1, {"dc": "running"}, "Reserve source active", "Резервне джерело працює", "Rezervni vir deluje"),
    ("alternative_source", 2003, 0x1, {"dc": "running", "dis": True}, "Alternative source active", "Альтернативне джерело працює", "Alternativni vir deluje"),
    ("alternative_source_pump", 2087, 0x1, {"dc": "running", "dis": True}, "Alternative source pump", "Насос альтернативного джерела", "Črpalka alternativnega vira"),
    ("dhw_quick_heating_active", 2009, 0x1, {"dc": "running"}, "DHW quick heating active", "Швидкий нагрів води активний", "Hitro segrevanje aktivno"),
    ("remote_activation", 2038, 0x1, {}, "Remote activation", "Дистанційне ввімкнення", "Daljinski vklop"),
    ("error_shown", 2112, 0x1, {"dc": "problem"}, "Error shown", "Помилка на дисплеї", "Prikazana napaka"),
    ("cascade_1", 2359, 0x1, {"dc": "running", "dis": True}, "Cascade 1 running", "Каскад 1 працює", "Kaskada 1 deluje"),
    ("cascade_2", 2359, 0x2, {"dc": "running", "dis": True}, "Cascade 2 running", "Каскад 2 працює", "Kaskada 2 deluje"),
    ("cascade_3", 2359, 0x4, {"dc": "running", "dis": True}, "Cascade 3 running", "Каскад 3 працює", "Kaskada 3 deluje"),
    ("cascade_4", 2359, 0x8, {"dc": "running", "dis": True}, "Cascade 4 running", "Каскад 4 працює", "Kaskada 4 deluje"),
]

CIRCUIT_MODE = {"off": 0, "normal": 1, "schedule": 2}
CIRCUIT_MODE_NAMES = {
    "off": ("Off", "Вимкнено", "Izklop"),
    "normal": ("Normal", "Звичайний", "Normalno"),
    "schedule": ("Schedule", "За розкладом", "Po urniku"),
}
SELECTS = [
    ("mode", 2016, {"map": {"cooling": 1, "heating": 2, "auto": 3, "off": 4}, "low_byte": True},
     ("Mode", "Режим", "Režim"),
     {"cooling": ("Cooling", "Охолодження", "Hlajenje"), "heating": ("Heating", "Опалення", "Ogrevanje"),
      "auto": ("Auto", "Авто", "Samodejno"), "off": ("Off", "Вимкнено", "Izklop")}),
    ("program", 2012, {"map": {"normal": 0, "eco": 1, "comfort": 2}},
     ("Program", "Програма", "Program"),
     {"normal": ("Normal", "Звичайна", "Normalno"), "eco": ("ECO", "ECO", "ECO"), "comfort": ("COMFORT", "COMFORT", "COMFORT")}),
    ("dhw_mode", 2025, {"map": CIRCUIT_MODE}, ("DHW mode", "Гаряча вода: режим", "Sanitarna voda: režim"), CIRCUIT_MODE_NAMES),
    ("buffer_mode", 2034, {"map": CIRCUIT_MODE}, ("Buffer tank mode", "Бак: режим", "Zalogovnik: režim"), CIRCUIT_MODE_NAMES),
    ("loop_1_mode", 2041, {"map": CIRCUIT_MODE}, ("Loop 1 mode", "Контур 1: режим", "Krog 1: režim"), CIRCUIT_MODE_NAMES),
    ("loop_2_mode", 2051, {"map": CIRCUIT_MODE, "dis": True}, ("Loop 2 mode", "Контур 2: режим", "Krog 2: režim"), CIRCUIT_MODE_NAMES),
    ("loop_3_mode", 2061, {"map": CIRCUIT_MODE, "dis": True}, ("Loop 3 mode", "Контур 3: режим", "Krog 3: režim"), CIRCUIT_MODE_NAMES),
    ("loop_4_mode", 2071, {"map": CIRCUIT_MODE, "dis": True}, ("Loop 4 mode", "Контур 4: режим", "Krog 4: režim"), CIRCUIT_MODE_NAMES),
    ("pool_mode", 2080, {"map": CIRCUIT_MODE, "dis": True}, ("Pool mode", "Басейн: режим", "Bazen: režim"), CIRCUIT_MODE_NAMES),
]

SWITCHES = [
    ("heat_pump_enabled", 2011, {}, "Heat pump enabled", "Тепловий насос увімкнено", "Toplotna črpalka vklopljena"),
    ("dhw_quick_heating", 2014, {}, "DHW quick heating", "Швидкий нагрів води", "Hitro segrevanje sanitarne vode"),
    ("dhw_circulation", 2327, {}, "DHW circulation", "Циркуляція гарячої води", "Cirkulacija sanitarne vode"),
    ("vacation", 2021, {}, "Vacation mode", "Режим відпустки", "Dopust"),
    ("allow_additional_source", 2015, {"cat": "config"}, "Allow additional source", "Дозволити додаткове джерело", "Dovoli dodatni vir"),
    ("allow_reserve_source", 2017, {"cat": "config"}, "Allow reserve source", "Дозволити резервне джерело", "Dovoli rezervni vir"),
    ("anti_legionella", 2300, {"cat": "config"}, "Anti-legionella", "Антилегіонела", "Termična dezinfekcija"),
    ("loop_1_adaptive_curve", 2319, {"cat": "config"}, "Loop 1 adaptive curve", "Контур 1: адаптивна крива", "Krog 1: adaptivna krivulja"),
    ("loop_2_adaptive_curve", 2320, {"cat": "config", "dis": True}, "Loop 2 adaptive curve", "Контур 2: адаптивна крива", "Krog 2: adaptivna krivulja"),
    ("loop_3_adaptive_curve", 2321, {"cat": "config", "dis": True}, "Loop 3 adaptive curve", "Контур 3: адаптивна крива", "Krog 3: adaptivna krivulja"),
    ("loop_4_adaptive_curve", 2322, {"cat": "config", "dis": True}, "Loop 4 adaptive curve", "Контур 4: адаптивна крива", "Krog 4: adaptivna krivulja"),
    ("remote_shutdown", 2196, {"dis": True}, "Remote shutdown", "Дистанційне вимкнення", "Daljinski izklop funkcij"),
    ("screed_drying", 2306, {"cat": "config", "dis": True}, "Screed drying", "Сушіння стяжки", "Sušenje estriha"),
    ("system_filling", 2323, {"cat": "config", "dis": True}, "Heating system filling", "Заповнення системи", "Polnjenje sistema"),
]

_T = {"unit": "°C", "mul": 10}
_OFF = {"min": -10, "max": 10, "step": 0.1, "unit": "°C", "mul": 10, "cat": "config"}
_CURVE = {"min": 10, "max": 60, "step": 0.5, "unit": "°C", "mul": 10, "cat": "config"}
NUMBERS = [
    ("dhw_target", 2022, {**_T, "min": 10, "max": 60, "step": 0.5}, "DHW target", "Гаряча вода: уставка", "Sanitarna voda: želena"),
    ("loop_1_target", 2186, {**_T, "min": 10, "max": 60, "step": 0.1}, "Loop 1 target", "Контур 1: бажана температура", "Krog 1: želena temperatura"),
    ("loop_2_target", 2048, {**_T, "min": 10, "max": 45, "step": 0.1, "dis": True}, "Loop 2 target", "Контур 2: бажана температура", "Krog 2: želena temperatura"),
    ("loop_3_target", 2058, {**_T, "min": 10, "max": 45, "step": 0.1, "dis": True}, "Loop 3 target", "Контур 3: бажана температура", "Krog 3: želena temperatura"),
    ("loop_4_target", 2068, {**_T, "min": 10, "max": 45, "step": 0.1, "dis": True}, "Loop 4 target", "Контур 4: бажана температура", "Krog 4: želena temperatura"),
    ("pool_target", 2078, {**_T, "min": 20, "max": 35, "step": 0.1, "dis": True}, "Pool target", "Басейн: уставка", "Bazen: želena"),
    ("eco_offset", 2039, _OFF, "ECO offset", "Зміщення ECO", "Odmik ECO"),
    ("comfort_offset", 2040, _OFF, "COMFORT offset", "Зміщення COMFORT", "Odmik COMFORT"),
    ("dhw_eco_offset", 2029, _OFF, "DHW ECO offset", "Гаряча вода: зміщення ECO", "Sanitarna voda: odmik ECO"),
    ("dhw_comfort_offset", 2030, _OFF, "DHW COMFORT offset", "Гаряча вода: зміщення COMFORT", "Sanitarna voda: odmik COMFORT"),
    ("loop_1_eco_offset", 2046, _OFF, "Loop 1 ECO offset", "Контур 1: зміщення ECO", "Krog 1: odmik ECO"),
    ("loop_1_comfort_offset", 2047, _OFF, "Loop 1 COMFORT offset", "Контур 1: зміщення COMFORT", "Krog 1: odmik COMFORT"),
    ("loop_2_eco_offset", 2056, {**_OFF, "dis": True}, "Loop 2 ECO offset", "Контур 2: зміщення ECO", "Krog 2: odmik ECO"),
    ("loop_2_comfort_offset", 2057, {**_OFF, "dis": True}, "Loop 2 COMFORT offset", "Контур 2: зміщення COMFORT", "Krog 2: odmik COMFORT"),
    ("loop_3_eco_offset", 2066, {**_OFF, "dis": True}, "Loop 3 ECO offset", "Контур 3: зміщення ECO", "Krog 3: odmik ECO"),
    ("loop_3_comfort_offset", 2067, {**_OFF, "dis": True}, "Loop 3 COMFORT offset", "Контур 3: зміщення COMFORT", "Krog 3: odmik COMFORT"),
    ("loop_4_eco_offset", 2076, {**_OFF, "dis": True}, "Loop 4 ECO offset", "Контур 4: зміщення ECO", "Krog 4: odmik ECO"),
    ("loop_4_comfort_offset", 2077, {**_OFF, "dis": True}, "Loop 4 COMFORT offset", "Контур 4: зміщення COMFORT", "Krog 4: odmik COMFORT"),
    ("pool_eco_offset", 2085, {**_OFF, "dis": True}, "Pool ECO offset", "Басейн: зміщення ECO", "Bazen: odmik ECO"),
    ("pool_comfort_offset", 2086, {**_OFF, "dis": True}, "Pool COMFORT offset", "Басейн: зміщення COMFORT", "Bazen: odmik COMFORT"),
    ("system_correction", 2013, {"min": -4, "max": 4, "step": 1, "unit": "°C", "mul": 1, "cat": "config"}, "System temperature correction", "Корекція температури системи", "Korekcija temperature sistema"),
    ("buffer_curve_low", 2307, {**_CURVE, "max": 70}, "Buffer curve at -15 °C", "Бак: крива при -15 °C", "Zalogovnik: krivulja pri -15 °C"),
    ("buffer_curve_high", 2312, {**_CURVE, "max": 70}, "Buffer curve at +15 °C", "Бак: крива при +15 °C", "Zalogovnik: krivulja pri +15 °C"),
    ("loop_1_curve_low", 2308, _CURVE, "Loop 1 curve at -15 °C", "Контур 1: крива при -15 °C", "Krog 1: krivulja pri -15 °C"),
    ("loop_1_curve_high", 2313, _CURVE, "Loop 1 curve at +15 °C", "Контур 1: крива при +15 °C", "Krog 1: krivulja pri +15 °C"),
    ("loop_2_curve_low", 2309, {**_CURVE, "dis": True}, "Loop 2 curve at -15 °C", "Контур 2: крива при -15 °C", "Krog 2: krivulja pri -15 °C"),
    ("loop_2_curve_high", 2314, {**_CURVE, "dis": True}, "Loop 2 curve at +15 °C", "Контур 2: крива при +15 °C", "Krog 2: krivulja pri +15 °C"),
    ("loop_3_curve_low", 2310, {**_CURVE, "dis": True}, "Loop 3 curve at -15 °C", "Контур 3: крива при -15 °C", "Krog 3: krivulja pri -15 °C"),
    ("loop_3_curve_high", 2315, {**_CURVE, "dis": True}, "Loop 3 curve at +15 °C", "Контур 3: крива при +15 °C", "Krog 3: krivulja pri +15 °C"),
    ("loop_4_curve_low", 2311, {**_CURVE, "dis": True}, "Loop 4 curve at -15 °C", "Контур 4: крива при -15 °C", "Krog 4: krivulja pri -15 °C"),
    ("loop_4_curve_high", 2316, {**_CURVE, "dis": True}, "Loop 4 curve at +15 °C", "Контур 4: крива при +15 °C", "Krog 4: krivulja pri +15 °C"),
    ("anti_legionella_temperature", 2301, {"min": 50, "max": 75, "step": 1, "unit": "°C", "mul": 10, "cat": "config"}, "Anti-legionella temperature", "Антилегіонела: температура", "Dezinfekcija: temperatura"),
    ("anti_legionella_period", 2302, {"min": 1, "max": 30, "step": 1, "unit": "d", "mul": 1, "cat": "config"}, "Anti-legionella period", "Антилегіонела: період", "Dezinfekcija: perioda"),
    ("anti_legionella_start", 2303, {"min": 0, "max": 1439, "step": 1, "unit": "min", "mul": 1, "cat": "config"}, "Anti-legionella start (min after midnight)", "Антилегіонела: початок (хв від півночі)", "Dezinfekcija: začetek (min po polnoči)"),
    ("vacation_days", 2138, {"min": 0, "max": 99, "step": 1, "unit": "d", "mul": 1}, "Vacation days", "Відпустка, днів", "Dopust, dni"),
    ("solar_buffer_target", 2304, {"min": 10, "max": 90, "step": 0.5, "unit": "°C", "mul": 10, "cat": "config", "dis": True}, "Solar buffer target", "Сонячний бак: уставка", "Solarni zalogovnik: želena"),
    ("solar_boiler_target", 2305, {"min": 10, "max": 90, "step": 0.5, "unit": "°C", "mul": 10, "cat": "config", "dis": True}, "Solar boiler target", "Сонячний бойлер: уставка", "Solarni bojler: želena"),
]

# Entities computed inside Home Assistant (not a register)
LOCAL = {
    "sensor": {
        "active_alarms": ("Active alarms", "Активні аварії", "Aktivni alarmi"),
        "active_warnings": ("Active warnings", "Активні попередження", "Aktivna opozorila"),
        "energy_heating": ("Energy heating", "Енергія: опалення", "Energija: ogrevanje"),
        "energy_dhw": ("Energy hot water", "Енергія: гаряча вода", "Energija: sanitarna voda"),
        "energy_other": ("Energy other", "Енергія: інше", "Energija: ostalo"),
        "energy_total_calculated": ("Energy total (calculated)", "Енергія: разом (розрахунок)", "Energija: skupaj (izračun)"),
        "energy_pumps": ("Energy pumps (estimate)", "Енергія: насоси (оцінка)", "Energija: črpalke (ocena)"),
        "pumps_power": ("Pumps power (estimate)", "Потужність насосів (оцінка)", "Moč črpalk (ocena)"),
    },
    "binary_sensor": {
        "problem": ("Problem", "Проблема", "Težava"),
    },
    "button": {
        "acknowledge_error": ("Acknowledge error", "Скинути помилку", "Potrdi napako"),
    },
    "number": {
        "main_pump_power": ("Main pump power", "Головний насос: потужність", "Glavna črpalka: moč"),
        "loop_1_pump_power": ("Loop 1 pump power", "Насос контуру 1: потужність", "Črpalka kroga 1: moč"),
        "dhw_pump_power": ("DHW pump power", "Насос гарячої води: потужність", "Črpalka sanitarne vode: moč"),
        "circulation_pump_power": ("Circulation pump power", "Циркуляційний насос: потужність", "Cirkulacijska črpalka: moč"),
    },
    "climate": {
        "dhw": ("Hot water", "Гаряча вода", "Sanitarna voda"),
        "buffer": ("Buffer tank", "Бак", "Zalogovnik"),
        "loop_1": ("Loop 1", "Контур 1", "Krog 1"),
        "loop_2": ("Loop 2", "Контур 2", "Krog 2"),
        "loop_3": ("Loop 3", "Контур 3", "Krog 3"),
        "loop_4": ("Loop 4", "Контур 4", "Krog 4"),
        "pool": ("Pool", "Басейн", "Bazen"),
    },
}
# fmt: on
