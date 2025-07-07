import subprocess
import sys
import time
import os
import signal
import platform


def main():
    """
    Runs all data simulators (SCADA, PLC, and GPS) in parallel.

    This script simplifies the process of generating a realistic, multi-stream
    test environment by launching all available data simulators as separate,
    concurrent processes.

    It monitors all processes and allows for graceful shutdown using Ctrl+C.
    """
    simulators = [
        "scada_simulator.py",
        "plc_simulator.py",
        "gps_simulator.py"
    ]

    # Verify that all simulator scripts exist
    for script in simulators:
        if not os.path.exists(script):
            print(f"Error: Simulator script '{script}' not found.")
            sys.exit(1)

    print("Starting all simulators...")
    print("\n".join([f"  -> {s}" for s in simulators]))
    print("\nPress Ctrl+C to stop all processes.")

    processes = []
    python_executable = sys.executable
    creationflags = 0
    if platform.system() == "Windows":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        for script in simulators:
            # Use the -u flag for unbuffered output
            proc = subprocess.Popen(
                [python_executable, "-u", script],
                stdout=sys.stdout,
                stderr=sys.stderr,
                text=True,
                start_new_session=(platform.system() != "Windows"),
                creationflags=creationflags
            )
            processes.append(proc)
            print(f"[INFO] Started '{script}' with PID: {proc.pid}")

        # Wait for any process to exit
        while True:
            for proc in processes:
                if proc.poll() is not None:
                    print(f"[WARN] Process '{proc.args[2]}' with PID {proc.pid} has terminated.")
                    # Trigger shutdown of all other processes
                    raise KeyboardInterrupt
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C received. Shutting down all simulators...")
        for proc in processes:
            try:
                if platform.system() == "Windows":
                    # proc.send_signal(signal.CTRL_C_EVENT)
                    os.kill(proc.pid, signal.CTRL_C_EVENT)
                else:
                    # proc.terminate()
                    os.kill(proc.pid, signal.SIGTERM) # More forceful
            except ProcessLookupError:
                print(f"[WARN] Process with PID {proc.pid} was already terminated.")
            except Exception as e:
                print(f"[ERROR] Could not terminate process {proc.pid}: {e}")

        # Wait for all processes to terminate
        for proc in processes:
            proc.wait()

        print("[INFO] All simulators have been shut down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
