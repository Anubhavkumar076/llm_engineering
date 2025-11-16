# user_app.py
import gradio as gr
from datetime import datetime
from gs_helper import open_sheet, list_my_appointments, append_appointment, find_occ_row, get_occ_values, update_occupied, read_appointments
import pandas as pd
import uuid

SPREADSHEET_NAME = "SalonBookings"


# ✅ Load data filtered by date
def load_day_data(date):
    sh = open_sheet(SPREADSHEET_NAME)
    df = read_occ_table(sh)
    if df.empty:
        return pd.DataFrame()
    return df[df["date"] == date]


# ✅ Step 1 — Fetch all salons for date
def get_salons(date):
    df = load_day_data(date)
    if df.empty:
        return []

    salons = sorted(df["salon_name"].dropna().unique().tolist())
    return salons


# ✅ Step 2 — Fetch locations for salon on selected date
def get_locations(date, salon):
    df = load_day_data(date)
    if df.empty:
        return []

    df = df[df["salon_name"] == salon]
    locations = sorted(df["location"].dropna().unique().tolist())
    return locations


# ✅ Step 3 — Fetch slots for salon + location + date
def get_slots(date, salon, location):
    df = load_day_data(date)
    if df.empty:
        return [], []

    df = df[(df["salon_name"] == salon) & (df["location"] == location)]

    slot_list = []
    display_info = []

    for _, row in df.iterrows():
        cap = int(row["capacity"])
        occ = int(row["occupied"])
        slot = row["slot_label"]

        if cap == 0:
            continue  # skip capacity 0

        full = occ >= cap

        label = f"{slot} ({occ}/{cap})"
        if not full:
            slot_list.append(slot)

        display_info.append(label + (" - FULL" if full else ""))

    return slot_list, display_info


# ✅ Step 4 — Fetch services for selected slot
def get_services(date, salon, location, slot):
    df = load_day_data(date)
    df = df[(df["salon_name"] == salon) &
            (df["location"] == location) &
            (df["slot_label"] == slot)]

    if df.empty:
        return []

    # services = CSV string => convert to array
    services_csv = df.iloc[0]["services"]
    if not services_csv:
        return []

    return [s.strip() for s in services_csv.split(",")]


# ✅ Booking logic
def book_slot(date, slot, salon, location, name, phone, service):
    sh = open_sheet(SPREADSHEET_NAME)

    rownum = find_occ_row(sh, date, slot, salon)
    if not rownum:
        return "Slot unavailable. Refresh and retry."

    rvals = get_occ_values(sh, rownum)
    capacity = int(rvals[2])
    occupied = int(rvals[3])

    if occupied >= capacity:
        return "Sorry, slot is full."

    update_occupied(sh, rownum, occupied + 1)

    appt = {
        "id": str(uuid.uuid4()),
        "date": date,
        "slot_label": slot,
        "salon_name": salon,
        "location": location,
        "name": name,
        "phone": phone,
        "service": service,
        "created_at": datetime.utcnow().isoformat()
    }
    append_appointment(sh, appt)

    return "✅ Booking successful!"


# ✅ UI
with gr.Blocks() as user_app:
    gr.Markdown("# Salon Booking")

    with gr.Row():
        with gr.Column():

            name = gr.Textbox(label="Your Name", lines=1)
            phone = gr.Textbox(label="Phone Number", lines=1)
            date = gr.Textbox(label="Date (YYYY-MM-DD)",
                              value=datetime.now().strftime("%Y-%m-%d"))

            salon = gr.Dropdown(label="Select Salon", choices=[])
            location = gr.Dropdown(label="Select Location", choices=[])
            slot = gr.Dropdown(label="Available Slots", choices=[])
            service = gr.Dropdown(label="Available Services", choices=[])

            btn_refresh = gr.Button("Refresh")
            btn_book = gr.Button("Book")

            result = gr.Textbox(label="Status", lines=2)

        with gr.Column():
            phone_lookup = gr.Textbox(label="Search Appointments by Phone")
            btn_list = gr.Button("List Appointments")
            list_view = gr.Textbox(label="Appointments", lines=10)

    # ✅ refresh button logic
    def refresh(date):
        salons = get_salons(date)
        return gr.update(choices=salons, value=salons[0] if salons else None)

    btn_refresh.click(refresh, inputs=[date], outputs=[salon])

    # ✅ When salon changes → update locations
    def on_salon_change(date, salon):
        locs = get_locations(date, salon)
        return gr.update(choices=locs, value=locs[0] if locs else None)

    salon.change(on_salon_change, inputs=[date, salon], outputs=[location])

    # ✅ When location changes → update slots
    def on_location_change(date, salon, location):
        slots, labels = get_slots(date, salon, location)
        return gr.update(choices=slots, value=slots[0] if slots else None), "\n".join(labels)

    location.change(on_location_change, inputs=[date, salon, location], outputs=[slot, result])

    # ✅ When slot changes → update services
    def on_slot_change(date, salon, location, slot):
        services = get_services(date, salon, location, slot)
        return gr.update(choices=services, value=services[0] if services else None)

    slot.change(on_slot_change, inputs=[date, salon, location, slot], outputs=[service])

    # ✅ Booking
    btn_book.click(book_slot, inputs=[
        date, slot, salon, location, name, phone, service
    ], outputs=result)

    # ✅ List appointments
    # btn_list.click(
    #     lambda phone: read_appointments if phone else "Enter phone",
    #     inputs=[phone_lookup],
    #     outputs=list_view
    # )

    btn_list.click(
        fn=list_my_appointments,
        inputs=[phone_lookup],
        outputs=[list_view]
    )


if __name__ == "__main__":
    user_app.launch()
