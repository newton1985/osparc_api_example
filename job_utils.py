import os
import time
import osparc
import numpy as np
from file_utils import extract_zipfile


def create_and_upload_job(files_api, solvers_api, project_name, e_index, zip_filepath, runner_solver_name, runner_solver_version):
    """Creates a job for the solver and uploads the necessary files."""
    start = time.time()
    
    # Upload the zip file
    input_file = files_api.upload_file(file=zip_filepath)
    
    # Get the solver release details
    solver = solvers_api.get_solver_release(runner_solver_name, runner_solver_version)
    
    # Create a job with the uploaded file as input
    job = solvers_api.create_job(solver.id, solver.version, osparc.JobInputs({"input_1": input_file}))
    
    end = time.time()
    print(f"time to upload file & create job: {end - start}")

    return (project_name, "electrode" + str(e_index).zfill(2)), (job.id, solver.id)


def monitor_jobs(solvers_api, metadata, runner_solver_version, check_interval=0.5):
    """Monitors the status of all jobs and waits for completion."""
    statuses = {}
    
    # Start each job and track its status
    print(metadata)
    for (project_name, e_idx), (jid, sid) in metadata.items():
        status = solvers_api.start_job(sid, runner_solver_version, jid)
        statuses[jid] = status
    
    # Continuously check if all jobs are done
    while not all_done(statuses):
        time.sleep(check_interval)
        for (project_name, e_idx), (jid, sid) in metadata.items():
            status = solvers_api.inspect_job(sid, runner_solver_version, jid)
            statuses[jid] = status
            print(f"Solver progress: {status.progress}/100", end='\r', flush=True)

    return statuses


def all_done(statuses):
    stopped = np.array([status.stopped_at for (jid, status) in statuses.items()])
    return np.all(stopped)


def download_results(files_api, solvers_api, metadata, runner_solver_version, result_dir):
    """Downloads and extracts job results after completion."""
    for (project_name, e_idx), (jid, sid) in metadata.items():
        outputs = solvers_api.get_job_outputs(sid, runner_solver_version, jid)
        logfile_path = solvers_api.get_job_output_logfile(sid, runner_solver_version, jid)
        
        # Determine if e_idx is a range or a single index
        if isinstance(e_idx, range):
            extract_path = os.path.join(result_dir, project_name)
        else:
            extract_path = os.path.join(result_dir, project_name, str(e_idx))

        # Extract log files
        extract_zipfile(logfile_path, extract_path)
        
        # Download and extract the results
        download_path = files_api.download_file(outputs.results["output_1"].id)
        extract_zipfile(download_path, extract_path)
