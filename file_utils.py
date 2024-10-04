import re
import os
import glob
import shutil
import zipfile
import s4l_v1.simulation.emlf as emlf

from string import Template


def zip_folder_handle(zipf, folder_path):
    """Helper function to recursively zip folder contents."""
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, start=os.path.dirname(folder_path))
            zipf.write(full_path, arcname)


def extract_zipfile(zip_filepath, extract_dir):
    """Extracts the contents of a zip file to a specified directory."""
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        

def parse_log(logfile, pattern):
    """Efficiently parse the log file for lines matching a pattern."""
    pattern_re = re.compile(re.escape(pattern) + r"(.+)$")  # Use regex to extract the part after the pattern
    results = []
    
    with open(logfile, 'r') as file:
        for line in file:
            match = pattern_re.search(line)
            if match:
                results.append(match.group(1).strip().split('/')[-1])
                
    return results


# Helper function to process a template file
def process_template(template_path, substitutions, output_path):
    """Generalized function to process a template and save the result."""
    with open(template_path, 'r') as f:
        src = Template(f.read())
        result = src.substitute(substitutions)
    with open(output_path, 'w') as f_output:
        f_output.write(result)
        

# Helper function to zip files and folders
def zip_files(output_zip, files_to_include, folders_to_include=None):
    """Generalized zipping function."""
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add files to the zip
        for file in files_to_include:
            basename = os.path.basename(file)
            if basename.startswith("main"):
                zipf.write(file, "main.py")
            else:
                zipf.write(file, basename)
        
        # Add folders to the zip (if provided)
        if folders_to_include:
            for folder in folders_to_include:
                zip_folder_handle(zipf, folder)
                

# Generalized staging method with fully parameterized file/folder zipping
def stage_simulation(project_name, electrode_info, template_path, home_dir, task_config):
    """
    A generalized staging method for different simulation tasks (EM simulation, current matrix, etc.).
    
    Args:
        project_name (str): The project name.
        electrode_info (int | range): Information about the electrode (could be an index or a range).
        template_path (str): Path to the template file.
        home_dir (str): Home directory where the staged files will be saved.
        task_config (dict): A dictionary containing task-specific configuration options such as:
            - 'template_vars': A dictionary of template variables.
            - 'file_suffix': The suffix for the output file (e.g., 'em_sim', 'J_matrix').
            - 'zip_files': A list of file paths to include in the zip.
            - 'zip_folders': A list of folder paths to include in the zip.
            - 'zipped_filename': The name of the resulting zip file.
    
    Returns:
        str: The path to the zipped simulation.
    """
    # Set up variables for template substitution
    template_vars = task_config.get('template_vars', {})
    file_suffix = task_config.get('file_suffix', 'sim')
    
    # Create a suffix for electrode information (handles range or single index)
    electrode_suffix = f"E{str(electrode_info).zfill(2)}" if isinstance(electrode_info, int) else f"E_{electrode_info.start}_{electrode_info.stop}"
    
    print(f'Staging {file_suffix} for {project_name}, on electrode {electrode_suffix}')
    
    # Path for the staged file
    staging_file_name = f'main_{file_suffix}_{project_name}_{electrode_suffix}.py'
    staging_file_path = os.path.join(home_dir, 'staging', staging_file_name)
    
    # Process the template and save the result
    process_template(template_path, template_vars, staging_file_path)
    
    # Set up zip file name and path
    zip_filename = task_config.get('zipped_filename', f'{file_suffix}_{project_name}_{electrode_suffix}.zip')
    zip_filepath = os.path.join(home_dir, 'staging', zip_filename)
    
    # Gather files and folders to zip from task_config
    files_to_zip = [staging_file_path] + task_config.get('zip_files', [])
    folders_to_zip = task_config.get('zip_folders', [])
    
    # Zip the specified files and folders
    zip_files(zip_filepath, files_to_zip, folders_to_zip)
    
    return zip_filepath


def process_simulation(el, project_name, home_dir, res_path):
    """Process each simulation for a given electrode."""
    log_file_path = glob.glob(os.path.join(home_dir, f"output/{project_name}/{el}/*logs"))
    if not log_file_path:
        print(f"No logs found for electrode {el}")
        return
    
    log_file = log_file_path[0]
    old_ID_mock, old_ID_lf = parse_log(log_file, "Output file name: ")
    
    # Process mock simulation
    fn_mock_src = os.path.join(home_dir, f'output/{project_name}/{el}/{old_ID_mock}')
    if os.path.isfile(fn_mock_src):
        sim_mock = emlf.ElectroQsOhmicSimulation()
        sim_mock.Name = f"Subject_Anisotropy_{el}"
        new_ID_mock = sim_mock.GetOutputFileName().split('/')[-1]
        
        fn_mock_dest = os.path.join(res_path, new_ID_mock)
        shutil.move(fn_mock_src, fn_mock_dest)

    # Process LF simulation
    fn_lf_src = os.path.join(home_dir, f'output/{project_name}/{el}/{old_ID_lf}')
    if os.path.isfile(fn_lf_src):
        sim_lf = emlf.ElectroQsOhmicSimulation()
        sim_lf.Name = f"Monopolar stim - {el}"
        new_ID_lf = sim_lf.GetOutputFileName().split('/')[-1]

        fn_lf_dest = os.path.join(res_path, new_ID_lf)
        shutil.move(fn_lf_src, fn_lf_dest)
        
    return sim_mock, sim_lf
