from mpi4py import MPI
import tkinter as tk
import threading
import time
import random
import sys

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

SIMULATE_DELAY = 0.5
TIME_QUANTUM = 2

pause_flag = threading.Event()
pause_flag.set()

stop_simulation = threading.Event()

def worker_process():
    while True:
        msg = comm.recv(source=0)
        if msg[0] == "STOP":
            break
        pid, burst = msg
        time.sleep(SIMULATE_DELAY * burst)
        new_burst = max(0, burst - TIME_QUANTUM)
        comm.send(new_burst, dest=0)

if rank == 0:
    root = tk.Tk()
    root.title("MPI OS Simulation")
    root.geometry("650x600")

    tk.Label(root, text="MPI OS Scheduler", font=("Arial", 18, "bold")).pack(pady=10)

    time_label = tk.Label(root, text="Time: 0", font=("Arial", 14))
    time_label.pack()

    algo_var = tk.StringVar(value="Round Robin")
    algo_menu = tk.OptionMenu(root, algo_var, "Round Robin", "FCFS")
    algo_menu.pack(pady=5)

    cpu_labels = []
    for i in range(1, size):
        label = tk.Label(root, text=f"CPU {i}: Idle", font=("Arial", 12), width=50, bg="lightgray")
        label.pack(pady=2)
        cpu_labels.append(label)

    control_frame = tk.Frame(root)
    control_frame.pack(pady=10)

    def pause_sim():
        pause_flag.clear()
        log("⏸️ Simulation Paused.")

    def resume_sim():
        pause_flag.set()
        log("▶️ Simulation Resumed.")

    def reset_sim():
        stop_simulation.set()
        pause_flag.set()
        for label in cpu_labels:
            label.config(text="Idle", bg="lightgray")
        time_label.config(text="Time: 0")
        log("🔄 Reset simulation.")

    tk.Button(control_frame, text="Pause", command=pause_sim, width=10).grid(row=0, column=0, padx=5)
    tk.Button(control_frame, text="Resume", command=resume_sim, width=10).grid(row=0, column=1, padx=5)
    tk.Button(control_frame, text="Reset", command=reset_sim, width=10).grid(row=0, column=2, padx=5)

    log_frame = tk.Frame(root)
    log_frame.pack(pady=10)

    log_box = tk.Text(log_frame, height=10, width=80)
    log_box.pack()

    def log(message):
        log_box.insert(tk.END, f"{message}\n")
        log_box.see(tk.END)

    scheduler_thread = None

    def scheduler():
        algorithm = algo_var.get()
        log(f"🧠 Algorithm selected: {algorithm}")

        processes = []
        for i in range(6):
            processes.append({
                'pid': i + 1,
                'burst': random.randint(4, 10),
                'arrival': i
            })

        queue = processes.copy()
        clock = 0
        stop_simulation.clear()

        log(f"📦 Scheduling started with {algorithm} algorithm...")

        while queue and not stop_simulation.is_set():
            pause_flag.wait()

            if algorithm == "FCFS":
                queue.sort(key=lambda p: p['arrival'])

            for i in range(1, size):
                if not queue or stop_simulation.is_set():
                    break

                process = queue.pop(0)
                run_time = TIME_QUANTUM if algorithm == "Round Robin" else process['burst']

                cpu_labels[i - 1].config(text=f"CPU {i}: Running P{process['pid']} ({run_time} units)", bg="lightgreen")
                log(f"🟢 CPU {i} → P{process['pid']} | Burst: {process['burst']} | Run: {run_time}")

                comm.send((process['pid'], run_time), dest=i)
                time.sleep(SIMULATE_DELAY * run_time)

                clock += run_time
                time_label.config(text=f"Time: {clock}")
                root.update()

                new_burst = comm.recv(source=i)
                process['burst'] = new_burst
                cpu_labels[i - 1].config(text=f"CPU {i}: Idle", bg="lightgray")

                if new_burst > 0 and algorithm == "Round Robin":
                    queue.append(process)
                elif algorithm == "FCFS":
                    log(f"✅ P{process['pid']} completed (FCFS)")

        if not stop_simulation.is_set():
            time_label.config(text=f"Time: {clock} (Complete)")
            log("🏁 Simulation Finished.")

    def start_simulation():
        log("▶️ Starting simulation...")
        global scheduler_thread
        scheduler_thread = threading.Thread(target=scheduler)
        scheduler_thread.start()

    def on_close():
        for i in range(1, size):
            comm.send(("STOP", 0), dest=i)
        root.destroy()
        sys.exit(0)

    start_button = tk.Button(root, text="Start Simulation", command=start_simulation, width=20, bg="lightblue", font=("Arial", 12, "bold"))
    start_button.pack(pady=10)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

else:
    worker_process()
