import sys
import importlib.util
import os

def check_package(package_name):
    """Checks if a package can be imported."""
    try:
        importlib.util.find_spec(package_name)
        return True
    except ImportError:
        return False

def get_import_name(requirement):
    """Extracts the import name from a requirements.txt line."""
    # Handle cases like package==version or package>=version
    package_part = requirement.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
    # Handle specific mappings if necessary (e.g., Pillow vs PIL)
    # For now, assume import name is the same as package name part,
    # except for known cases like Pillow.
    if package_part.lower() == 'pillow':
        return 'PIL'
    elif package_part.lower() == 'flask':
        return 'flask'
    elif package_part.lower() == 'jinja2':
        return 'jinja2'
    else:
        return package_part

if __name__ == "__main__":
    # Check if running in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("Error: Not running in a virtual environment.")
        print("Please activate your virtual environment before running this script.")
        sys.exit(1)

    missing_packages = []
    try:
        with open("requirements.txt", "r") as f:
            requirements = f.readlines()
    except FileNotFoundError:
        print("Error: requirements.txt not found.")
        sys.exit(1)

    for req in requirements:
        req = req.strip()
        if not req or req.startswith('#'):
            continue
        
        import_name = get_import_name(req)
        if not check_package(import_name):
            missing_packages.append(req)

    if missing_packages:
        print("The following packages are not installed in the virtual environment:")
        for pkg in missing_packages:
            print(pkg)
        sys.exit(1)
    else:
        #print("All required packages are installed in the virtual environment.")
        sys.exit(0)
