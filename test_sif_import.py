import sys
import logging
from pathlib import Path

# Add the repository to sys.path
sys.path.insert(0, "c:\\Github\\ANYstructure")

from anystruct.fe_plate_fields import read_sesam_shell_model, infer_plate_fields, detect_surface_patches, detect_cylinder_geometry
from anysolver.sesam_fem.sif_importer import import_sesam_fem

sif_path = "c:\\Github\\ANYstructure\\ref_cases\\20250926_134848__set_ANY_res_set_R1.SIF"

try:
    print("Reading SESAM FEM...")
    result = import_sesam_fem(sif_path, strict=False)
    print(f"Nodes: {len(result.document.nodes)}")
    print(f"Elements: {len(result.document.elements)}")
    
    print("\nReading SESAM shell model...")
    model = read_sesam_shell_model(sif_path)
    print(f"Shell elements: {len(model.shell_elements)}")
    print(f"Beam elements: {len(model.beam_elements)}")
    
    print("\nDetecting cylinder geometry...")
    try:
        geom = detect_cylinder_geometry(model)
        print("Detected as cylinder!")
    except Exception as e:
        print(f"Not a cylinder: {e}")
        
    print("\nDetecting surface patches...")
    patches = detect_surface_patches(model)
    print(f"Found {len(patches)} surface patches.")
    if patches:
        print(f"Largest patch elements: {len(patches[-1].element_ids)}")
        
    print("\nInferring plate fields...")
    fields = infer_plate_fields(model)
    print(f"Inferred {len(fields)} plate fields.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
