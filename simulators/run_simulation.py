import argparse
import subprocess
import sys
import time
import os
import threading
import signal
import platform


def stream_reader(stream, label):
    """
    Reads a stream (stdout or stderr) line by line and prints it with a label.

    This function runs in a separate thread for each stream to avoid blocking
    the main thread. It ensures that all output from the simulator and processor
    is captured and displayed in real-time.

    Args:
        stream: The stream to read from (stdout or stderr of a subprocess).
        label: A label to prefix each line of output, indicating the source.
    """
    with stream:
        for line in iter(stream.readline, b''):
            # Decode bytes to string if necessary
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            print(f"[{label}]: {line.strip()}")
        stream.close()


def main():
    """
    Runs a specified simulator and the event stream processor in parallel.

    This script simplifies the process of running a full simulation pipeline by
    launching the selected data simulator (SCADA, PLC, or GPS) and the
    corresponding event stream processor as two separate, concurrent processes.

    It monitors both processes and allows for graceful shutdown using Ctrl+C.
    """
    parser = argparse.ArgumentParser(
        description="Run a simulator and the event stream processor in tandem.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "stream_type",
        choices=["scada", "plc", "gps"],
        help="The type of stream to simulate and process.\n"
             "  - scada: Industrial control system data\n"
             "  - plc: Programmable logic controller data\n"
             "  - gps: GPS tracking data for logistics"
    )
    args = parser.parse_args()

    stream_type = args.stream_type.lower()
    simulator_script = f"{stream_type}_simulator.py"
    processor_script = "event_stream_processor.py"

    # Verify that the simulator script exists
    if not os.path.exists(simulator_script):
        print(f"Error: Simulator script '{simulator_script}' not found.")
        sys.exit(1)

    print(f"Starting simulation for stream type: '{stream_type}'")
    print(f"  -> Simulator: {simulator_script}")
    print(f"  -> Processor: {processor_script}")
    print("\nPress Ctrl+C to stop both processes.")

    simulator_process = None
    processor_process = None

    # The processor no longer uses an environment variable.
    # The stream_type is passed as a command-line argument.

    try:
        # Using sys.executable to ensure we use the same python interpreter
        # that is running this script. This is important for virtual environments.
        python_executable = sys.executable

        creationflags = 0
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        # Launch the processor first, passing the stream type as an argument
        # Use the -u flag for unbuffered output, ensuring we see logs in real-time.
        # Redirect stderr to stdout to prevent I/O deadlocks.
        processor_process = subprocess.Popen(
            [python_executable, "-u", processor_script, "--stream-type", stream_type],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=(platform.system() != "Windows"),
            creationflags=creationflags
        )
        print(f"[INFO] Processor PID: {processor_process.pid}")

        # Wait for the processor to signal that it's ready
        print("Waiting for the event stream processor to initialize...")
        while True:
            proc_output = processor_process.stdout.readline()
            if proc_output:
                # Display processor's startup output (which now includes stderr)
                stripped_output = proc_output.strip()
                print(f"[PROCESSOR - {stream_type.upper()}]: {stripped_output}")
                # Check for our specific ready signal
                if "PROCESSOR_READY" in stripped_output:
                    print("\nProcessor is ready. Starting the simulator.\n")
                    break # Exit the waiting loop

            # No longer need to check stderr separately as it's merged with stdout

            # If the process terminates before it's ready, it's an error
            if processor_process.poll() is not None:
                print("\nError: Processor terminated unexpectedly during startup.", file=sys.stderr)
                print("Please check the logs above for errors.", file=sys.stderr)
                sys.exit(1)

        # Now that the processor is ready, launch the simulator
        # Use the -u flag for unbuffered output.
        simulator_process = subprocess.Popen(
            [python_executable, "-u", simulator_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ,
            start_new_session=(platform.system() != "Windows"),
            creationflags=creationflags
        )
        print(f"[INFO] Simulator PID: {simulator_process.pid}")

        # --- Monitor processes using non-blocking threads ---
        labels = {
            "PROC_OUT": f"PROCESSOR - {stream_type.upper()}",
            "SIM_OUT": f"SIMULATOR - {stream_type.upper()}",
            "SIM_ERR": f"SIMULATOR ERROR - {stream_type.upper()}"
        }

        # The processor's stderr is already redirected to its stdout,
        # so we only need to read one stream for it.
        proc_out_thread = threading.Thread(
            target=stream_reader, args=(processor_process.stdout, labels["PROC_OUT"])
        )
        sim_out_thread = threading.Thread(
            target=stream_reader, args=(simulator_process.stdout, labels["SIM_OUT"])
        )
        sim_err_thread = threading.Thread(
            target=stream_reader, args=(simulator_process.stderr, labels["SIM_ERR"])
        )

        threads = [proc_out_thread, sim_out_thread, sim_err_thread]
        for t in threads:
            t.start()

        # Wait for the main processes to complete.
        # The main loop now just waits, while the threads handle I/O.
        while simulator_process.poll() is None:
            # Check if the processor died unexpectedly
            if processor_process.poll() is not None:
                print("\nError: Processor terminated unexpectedly while the simulator was running.", file=sys.stderr)
                break
            time.sleep(0.5)

        # If the loop was broken by the simulator finishing, terminate the processor
        if simulator_process.poll() is not None:
            print(f"\nSimulator process finished with code {simulator_process.returncode}.")
            print("Terminating processor...")
            processor_process.terminate()

        # Wait for all reader threads to finish
        for t in threads:
            t.join()

        print("All processes and reader threads have completed.")

    except KeyboardInterrupt:
        print("\nCtrl+C received. Terminating processes...")
        killed = False
        procs = [simulator_process, processor_process]
        if platform.system() == "Windows":
            import getpass
            user = getpass.getuser()
            for proc in procs:
                if proc and proc.poll() is None:
                    try:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)])
                        print(f"Process {proc.pid} forcefully killed with taskkill.")
                    except Exception as e:
                        print(f"taskkill failed: {e}")
            # As a last resort, kill all python.exe processes for this user started in the last 10 minutes
            print("[INFO] Attempting to kill any remaining python.exe processes for this user...")
            try:
                subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", f"USERNAME eq {user}"])
            except Exception as e:
                print(f"Final taskkill failed: {e}")
            killed = True
        else:
            for proc in procs:
                if proc and proc.poll() is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except Exception:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
            if simulator_process:
                sim_rc = simulator_process.wait()
                print(f"Simulator terminated with return code: {sim_rc}")
            if processor_process:
                proc_rc = processor_process.wait()
                print(f"Processor terminated with return code: {proc_rc}")
        if killed:
            print("All processes forcefully killed.")
        print("Simulation stopped.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        # Ensure processes are cleaned up
        for proc in [simulator_process, processor_process]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
    finally:
        # Final check to ensure processes are terminated
        for proc in [simulator_process, processor_process]:
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
