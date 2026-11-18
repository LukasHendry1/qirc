# One scheduled dose. Used by the GetSchedule and SetSchedule services.

uint8 hour              # 0-23, local time
uint8 minute            # 0-59
uint8 dispenser_id      # which dispenser holds this medication (0 or 1)
uint8 pill_count        # pills to dispense
string label            # e.g. "Morning vitamins"
