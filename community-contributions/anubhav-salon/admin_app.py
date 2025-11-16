# admin_app.py
import gradio as gr
from datetime import datetime, timedelta
from gs_helper import open_sheet, read_occ_table, read_appointments, append_appointment, find_occ_row, get_occ_values, update_occupied
import pandas as pd

SPREADSHEET_NAME = "SalonBookings"  # change to your sheet name


# Plain python code to generate half-hour slots like 07:00-07:30, 07:30-08:00...
def list_default_slots(start_hour=7, end_hour=23):
    slots = []
    cur = datetime(2000,1,1, start_hour, 0)
    end = datetime(2000,1,1, end_hour, 0)
    while cur < end:
        nextt = cur + timedelta(minutes=30)
        slots.append(f"{cur.strftime('%H:%M')}-{nextt.strftime('%H:%M')}")
        cur = nextt
    return slots


def create_or_update_slot(date, slot_label, capacity, services="", salon_name="", location=""):
    
    progress=gr.Progress()

    progress(0.1, desc="Connecting to sheet")

    sh = open_sheet(SPREADSHEET_NAME)

    progress(0.4, desc="Checking slot")
    # find if row exists
    rownum = find_occ_row(sh, date, slot_label, salon_name)
    ws = sh.worksheet("occupancy")

    progress(0.7, desc="Processing data")
    
    if rownum:
        # update capacity (column C)
        ws.update_cell(rownum, 3, capacity)
        ws.update_cell(rownum, 5, services)
        ws.update_cell(rownum, 6, salon_name)
        ws.update_cell(rownum, 7, location)
        msg = f"✅ Updated {slot_label}"
    else:
        ws.append_row([date, slot_label, capacity, 0, services, salon_name, location], value_input_option='USER_ENTERED')
        msg = f"✅ Created {slot_label}"

    progress(1.0, desc="Done")

    return gr.update(value=msg, visible=True)

def view_occupancy(date, salon_name=""):
    sh = open_sheet(SPREADSHEET_NAME)
    df = read_occ_table(sh)
    if df.empty:
        return "No occupancy rows"
    df = df[df['date'] == date]
    if salon_name:
        df = df[df.get('salon_name','') == salon_name]
    if df.empty:
        return f"No slots for {date}"
    # present as string
    return df[['slot_label','capacity','occupied','services']].to_string(index=False)

def view_appointments(date=""):
    sh = open_sheet(SPREADSHEET_NAME)
    df = read_appointments(sh)
    if df.empty:
        return "No appointments"
    if date:
        df = df[df['date'] == date]
    if df.empty:
        return "No appointments for selected date"
    return df.to_string(index=False)

# Build Gradio UI
with gr.Blocks() as admin_app:
    gr.Markdown("# Salon Admin")
    with gr.Row():
        with gr.Column():
            salon_name = gr.Textbox(label="Salon Name", value="My Salon")
            location = gr.Textbox(label="Location", value="Delhi")
            date = gr.Textbox(label="Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
            slot = gr.Dropdown(label="Time Slot", choices=list_default_slots())
            capacity = gr.Number(label="Capacity (persons)", value=3, precision=0)
            services = gr.Textbox(label="Services (comma-separated)", value="Haircut,Shaving,Detan")
            btn_create = gr.Button("Create / Update Slot")
            toast = gr.Markdown(visible=False)
        with gr.Column():
            date_view = gr.Textbox(label="Date to View", value=datetime.now().strftime("%Y-%m-%d"))
            salon_view = gr.Textbox(label="Salon Name (optional)")
            btn_view = gr.Button("View Occupancy")
            occ_view = gr.Textbox(label="Occupancy List", lines=15)
            btn_view_appt = gr.Button("View Appointments")
            appt_view = gr.Textbox(label="Appointments List", lines=10)
    btn_create.click(create_or_update_slot, inputs=[date, slot, capacity, services, salon_name, location], outputs= toast)
    btn_view.click(view_occupancy, inputs=[date_view, salon_view], outputs=occ_view)
    btn_view_appt.click(view_appointments, inputs=[date_view], outputs=appt_view)

if __name__ == "__main__":
    admin_app.launch()
