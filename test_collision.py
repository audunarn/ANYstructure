import traceback
from anysolver import runtime as fe_solver
import numpy as np

flat = {
    'geometry': 'flat panel',
    'length_m': 2.0,
    'width_m': 1.5,
    'thickness_m': 0.012,
    'has_stiffener': True,
    'has_girder': False,
    'stiffener_spacing_m': 0.75
}
config = fe_solver.LightweightFEMConfig(
    mesh_fidelity='coarse',
    boundary_condition='clamped',
    collision_enabled=True,
    collision_adaptive_mesh_enabled=True,
    collision_adaptive_fine_size_m=0.06,
    collision_adaptive_extent_m=0.3,
    collision_radius_m=0.15,
    collision_start_x_m=1.0,
    collision_start_y_m=0.75,
    collision_start_z_m=0.3,
    collision_vector_x=0.0,
    collision_vector_y=0.0,
    collision_vector_z=-1.0,
    collision_mass_kg=200.0,
    collision_speed_mps=3.0,
    collision_material_nonlinear_enabled=True,
    detail_transition_style='local patch (quad+tri)'
)

try:
    generated_geometry = fe_solver.build_generated_geometry(flat, config)
    backend_config = fe_solver._full_backend.AnyStructureFEMConfig()
    model = fe_solver._full_backend.build_fe_model_from_generated_geometry(generated_geometry, backend_config)
    fe_solver._apply_material_curve_to_model(model, 'S355', {})
    load_case = fe_solver._full_backend.LoadCase('anystructure_symmetric_load')
    diagnostics = []
    
    constraint_mode = fe_solver._constraint_mode(config, flat)
    fe_solver._backend_solve_linear(model, load_case, solver_type=backend_config.solver_type, constraint_mode=constraint_mode, allow_unbalanced_free_free=fe_solver._allow_unbalanced_free_free(config, flat))
    fe_solver._run_collision_response(model, load_case, generated_geometry, flat, config, diagnostics)
except Exception as e:
    traceback.print_exc()
