import argparse
import subprocess
import sys
import time
import os
import threading


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

    # The processor no longer uses an environment variable.
    # The stream_type is passed as a command-line argument.

    try:
        # Using sys.executable to ensure we use the same python interpreter
        # that is running this script. This is important for virtual environments.
        python_executable = sys.executable

        # Launch the processor first, passing the stream type as an argument
        # Use the -u flag for unbuffered output, ensuring we see logs in real-time.
        # Redirect stderr to stdout to prevent I/O deadlocks.
        processor_process = subprocess.Popen(
            [python_executable, "-u", processor_script, "--stream-type", stream_type],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

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
            env=os.environ # The simulator doesn't need the STREAM_TYPE env var
        )

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
        simulator_process.terminate()
        processor_process.terminate()
        # Wait for processes to terminate
        sim_rc = simulator_process.wait()
        proc_rc = processor_process.wait()
        print(f"Simulator terminated with return code: {sim_rc}")
        print(f"Processor terminated with return code: {proc_rc}")
        print("Simulation stopped.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        # Ensure processes are cleaned up
        if 'simulator_process' in locals() and simulator_process.poll() is None:
            simulator_process.terminate()
        if 'processor_process' in locals() and processor_process.poll() is None:
            processor_process.terminate()
    finally:
        # Final check to ensure processes are terminated
        if 'simulator_process' in locals() and simulator_process.poll() is None:
            simulator_process.kill()
        if 'processor_process' in locals() and processor_process.poll() is None:
            processor_process.kill()


if __name__ == "__main__":
    main()
