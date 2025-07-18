"""
Auto-Fix System for BlendPro: AI Co-Pilot
One-click fixes for common scene issues
"""

import bpy
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..config.settings import get_settings
from ..utils.code_executor import get_code_executor
from ..utils.backup_manager import get_backup_manager
from .scene_monitor import get_scene_health_monitor, SceneIssue, IssueSeverity

class FixResult(Enum):
    """Results of auto-fix attempts"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"

@dataclass
class AutoFix:
    """Represents an automatic fix"""
    fix_id: str
    name: str
    description: str
    applicable_categories: List[str]
    applicable_severities: List[IssueSeverity]
    fix_function: Callable
    requires_backup: bool = True
    batch_capable: bool = False

class AutoFixSystem:
    """Manages automatic fixes for scene issues"""
    
    def __init__(self):
        self.settings = get_settings()
        self.code_executor = get_code_executor()
        self.backup_manager = get_backup_manager()
        self.scene_monitor = get_scene_health_monitor()
        
        # Register built-in fixes
        self._fixes: Dict[str, AutoFix] = {}
        self._register_builtin_fixes()
    
    def _register_builtin_fixes(self) -> None:
        """Register built-in auto-fixes"""
        
        # Geometry fixes
        self.register_fix(AutoFix(
            fix_id="remove_doubles",
            name="Remove Duplicate Vertices",
            description="Remove duplicate vertices from selected mesh objects",
            applicable_categories=["geometry"],
            applicable_severities=[IssueSeverity.WARNING, IssueSeverity.INFO],
            fix_function=self._fix_remove_doubles,
            batch_capable=True
        ))
        
        self.register_fix(AutoFix(
            fix_id="fix_non_manifold",
            name="Fix Non-Manifold Geometry",
            description="Attempt to fix non-manifold geometry issues",
            applicable_categories=["geometry"],
            applicable_severities=[IssueSeverity.WARNING],
            fix_function=self._fix_non_manifold
        ))
        
        self.register_fix(AutoFix(
            fix_id="remove_loose_vertices",
            name="Remove Loose Vertices",
            description="Remove loose vertices from mesh objects",
            applicable_categories=["geometry"],
            applicable_severities=[IssueSeverity.INFO],
            fix_function=self._fix_loose_vertices,
            batch_capable=True
        ))
        
        # Material fixes
        self.register_fix(AutoFix(
            fix_id="assign_basic_materials",
            name="Assign Basic Materials",
            description="Assign basic materials to objects without materials",
            applicable_categories=["materials"],
            applicable_severities=[IssueSeverity.INFO],
            fix_function=self._fix_assign_basic_materials,
            batch_capable=True
        ))
        
        self.register_fix(AutoFix(
            fix_id="remove_unused_materials",
            name="Remove Unused Materials",
            description="Remove materials that are not used by any objects",
            applicable_categories=["materials"],
            applicable_severities=[IssueSeverity.INFO],
            fix_function=self._fix_remove_unused_materials,
            requires_backup=False
        ))
        
        # Lighting fixes
        self.register_fix(AutoFix(
            fix_id="add_basic_lighting",
            name="Add Basic Lighting",
            description="Add basic three-point lighting setup",
            applicable_categories=["lighting"],
            applicable_severities=[IssueSeverity.WARNING],
            fix_function=self._fix_add_basic_lighting
        ))
        
        self.register_fix(AutoFix(
            fix_id="normalize_light_energy",
            name="Normalize Light Energy",
            description="Adjust overly bright lights to reasonable levels",
            applicable_categories=["lighting"],
            applicable_severities=[IssueSeverity.WARNING],
            fix_function=self._fix_normalize_light_energy,
            batch_capable=True
        ))
        
        # Render fixes
        self.register_fix(AutoFix(
            fix_id="set_active_camera",
            name="Set Active Camera",
            description="Set the first available camera as active, or create one",
            applicable_categories=["render"],
            applicable_severities=[IssueSeverity.WARNING],
            fix_function=self._fix_set_active_camera
        ))
        
        # Performance fixes
        self.register_fix(AutoFix(
            fix_id="add_decimate_modifiers",
            name="Add Decimate Modifiers",
            description="Add decimate modifiers to high-polygon objects",
            applicable_categories=["performance"],
            applicable_severities=[IssueSeverity.WARNING],
            fix_function=self._fix_add_decimate_modifiers,
            batch_capable=True
        ))
        
        # Organization fixes
        self.register_fix(AutoFix(
            fix_id="rename_default_objects",
            name="Rename Default Objects",
            description="Give descriptive names to objects with default names",
            applicable_categories=["organization"],
            applicable_severities=[IssueSeverity.SUGGESTION],
            fix_function=self._fix_rename_default_objects,
            batch_capable=True,
            requires_backup=False
        ))
    
    def register_fix(self, fix: AutoFix) -> None:
        """Register a new auto-fix"""
        self._fixes[fix.fix_id] = fix
    
    def get_applicable_fixes(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get fixes applicable to given issues"""
        
        applicable_fixes = []
        
        for fix in self._fixes.values():
            # Check if fix applies to any of the issues
            applicable_issues = []
            
            for issue in issues:
                issue_category = issue.get("category", "")
                issue_severity = IssueSeverity(issue.get("severity", "INFO"))
                
                if (issue_category in fix.applicable_categories and
                    issue_severity in fix.applicable_severities):
                    applicable_issues.append(issue)
            
            if applicable_issues:
                applicable_fixes.append({
                    "fix_id": fix.fix_id,
                    "name": fix.name,
                    "description": fix.description,
                    "applicable_issues": applicable_issues,
                    "batch_capable": fix.batch_capable,
                    "requires_backup": fix.requires_backup
                })
        
        return applicable_fixes
    
    def apply_fix(self, fix_id: str, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply a specific fix"""
        
        if fix_id not in self._fixes:
            return {"result": FixResult.FAILED, "error": f"Fix '{fix_id}' not found"}
        
        fix = self._fixes[fix_id]
        
        try:
            # Create backup if required
            backup_path = None
            if fix.requires_backup and self.settings.enable_auto_backup:
                backup_path = self.backup_manager.create_backup(force=True)
            
            # Apply the fix
            result = fix.fix_function(context, target_objects)
            
            return {
                "result": result.get("result", FixResult.SUCCESS),
                "message": result.get("message", f"Applied fix: {fix.name}"),
                "details": result.get("details", {}),
                "backup_created": backup_path is not None,
                "backup_path": backup_path
            }
            
        except Exception as e:
            return {
                "result": FixResult.FAILED,
                "error": f"Fix failed: {str(e)}",
                "backup_created": backup_path is not None,
                "backup_path": backup_path
            }
    
    def apply_multiple_fixes(
        self, 
        fix_ids: List[str], 
        context,
        target_objects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Apply multiple fixes in sequence"""
        
        results = []
        overall_success = True
        backup_path = None
        
        # Create single backup for all fixes
        if self.settings.enable_auto_backup:
            backup_path = self.backup_manager.create_backup(force=True)
        
        for fix_id in fix_ids:
            result = self.apply_fix(fix_id, context, target_objects)
            result["backup_created"] = False  # Don't create individual backups
            results.append(result)
            
            if result["result"] == FixResult.FAILED:
                overall_success = False
        
        return {
            "overall_success": overall_success,
            "results": results,
            "backup_created": backup_path is not None,
            "backup_path": backup_path
        }
    
    def auto_fix_scene(self, context, severity_threshold: IssueSeverity = IssueSeverity.WARNING) -> Dict[str, Any]:
        """Automatically fix all applicable issues in the scene"""
        
        # Analyze scene health
        health_report = self.scene_monitor.analyze_scene_health(context)
        
        if health_report.get("error"):
            return {"error": health_report["error"]}
        
        # Filter issues by severity
        issues = health_report.get("issues", [])
        filtered_issues = [
            issue for issue in issues
            if IssueSeverity(issue.get("severity", "INFO")).value in [
                IssueSeverity.CRITICAL.value, 
                IssueSeverity.WARNING.value
            ] if severity_threshold in [IssueSeverity.CRITICAL, IssueSeverity.WARNING]
        ]
        
        if not filtered_issues:
            return {
                "message": "No issues found that can be auto-fixed",
                "issues_analyzed": len(issues),
                "fixes_applied": 0
            }
        
        # Get applicable fixes
        applicable_fixes = self.get_applicable_fixes(filtered_issues)
        
        if not applicable_fixes:
            return {
                "message": "No auto-fixes available for current issues",
                "issues_found": len(filtered_issues),
                "fixes_applied": 0
            }
        
        # Apply fixes
        fix_ids = [fix["fix_id"] for fix in applicable_fixes]
        result = self.apply_multiple_fixes(fix_ids, context)
        
        successful_fixes = sum(1 for r in result["results"] if r["result"] == FixResult.SUCCESS)
        
        return {
            "message": f"Auto-fix completed: {successful_fixes}/{len(fix_ids)} fixes successful",
            "issues_found": len(filtered_issues),
            "fixes_applied": successful_fixes,
            "fixes_failed": len(fix_ids) - successful_fixes,
            "details": result,
            "backup_created": result.get("backup_created", False)
        }

    # Built-in fix implementations
    def _fix_remove_doubles(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Remove duplicate vertices from mesh objects"""

        objects_to_fix = self._get_target_mesh_objects(context, target_objects)

        if not objects_to_fix:
            return {"result": FixResult.NOT_APPLICABLE, "message": "No mesh objects to fix"}

        fixed_count = 0

        for obj in objects_to_fix:
            try:
                # Switch to edit mode
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')

                # Select all and remove doubles
                bpy.ops.mesh.select_all(action='SELECT')
                result = bpy.ops.mesh.remove_doubles(threshold=0.0001)

                # Switch back to object mode
                bpy.ops.object.mode_set(mode='OBJECT')

                if result == {'FINISHED'}:
                    fixed_count += 1

            except Exception as e:
                print(f"Failed to remove doubles from {obj.name}: {e}")
                continue

        if fixed_count > 0:
            return {
                "result": FixResult.SUCCESS,
                "message": f"Removed duplicate vertices from {fixed_count} object(s)",
                "details": {"objects_fixed": fixed_count}
            }
        else:
            return {"result": FixResult.FAILED, "message": "Failed to remove doubles from any objects"}

    def _fix_non_manifold(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fix non-manifold geometry"""

        objects_to_fix = self._get_target_mesh_objects(context, target_objects)

        if not objects_to_fix:
            return {"result": FixResult.NOT_APPLICABLE, "message": "No mesh objects to fix"}

        fixed_count = 0

        for obj in objects_to_fix:
            try:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')

                # Select non-manifold geometry
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.mesh.select_non_manifold()

                # Try to fix by filling holes and removing doubles
                bpy.ops.mesh.fill_holes(sides=4)
                bpy.ops.mesh.remove_doubles()

                bpy.ops.object.mode_set(mode='OBJECT')
                fixed_count += 1

            except Exception as e:
                print(f"Failed to fix non-manifold geometry in {obj.name}: {e}")
                continue

        return {
            "result": FixResult.SUCCESS if fixed_count > 0 else FixResult.FAILED,
            "message": f"Attempted to fix non-manifold geometry in {fixed_count} object(s)",
            "details": {"objects_processed": fixed_count}
        }

    def _fix_loose_vertices(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Remove loose vertices"""

        objects_to_fix = self._get_target_mesh_objects(context, target_objects)

        if not objects_to_fix:
            return {"result": FixResult.NOT_APPLICABLE, "message": "No mesh objects to fix"}

        fixed_count = 0

        for obj in objects_to_fix:
            try:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')

                # Select loose vertices
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.mesh.select_loose()

                # Delete loose vertices
                bpy.ops.mesh.delete(type='VERT')

                bpy.ops.object.mode_set(mode='OBJECT')
                fixed_count += 1

            except Exception as e:
                print(f"Failed to remove loose vertices from {obj.name}: {e}")
                continue

        return {
            "result": FixResult.SUCCESS if fixed_count > 0 else FixResult.FAILED,
            "message": f"Removed loose vertices from {fixed_count} object(s)",
            "details": {"objects_fixed": fixed_count}
        }

    def _fix_assign_basic_materials(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Assign basic materials to objects without materials"""

        objects_to_fix = self._get_target_mesh_objects(context, target_objects)
        objects_without_materials = [obj for obj in objects_to_fix if len(obj.material_slots) == 0]

        if not objects_without_materials:
            return {"result": FixResult.NOT_APPLICABLE, "message": "All objects already have materials"}

        # Create basic material if it doesn't exist
        basic_material = bpy.data.materials.get("BlendPro_Basic_Material")
        if not basic_material:
            basic_material = bpy.data.materials.new(name="BlendPro_Basic_Material")
            basic_material.use_nodes = True

            # Set up basic principled BSDF
            bsdf = basic_material.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.5

        # Assign material to objects
        assigned_count = 0
        for obj in objects_without_materials:
            try:
                obj.data.materials.append(basic_material)
                assigned_count += 1
            except Exception as e:
                print(f"Failed to assign material to {obj.name}: {e}")
                continue

        return {
            "result": FixResult.SUCCESS if assigned_count > 0 else FixResult.FAILED,
            "message": f"Assigned basic materials to {assigned_count} object(s)",
            "details": {"objects_fixed": assigned_count}
        }

    def _fix_remove_unused_materials(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Remove unused materials"""

        removed_count = 0
        materials_to_remove = []

        # Find unused materials
        for material in bpy.data.materials:
            if material.users == 0:
                materials_to_remove.append(material)

        # Remove unused materials
        for material in materials_to_remove:
            try:
                bpy.data.materials.remove(material)
                removed_count += 1
            except Exception as e:
                print(f"Failed to remove material {material.name}: {e}")
                continue

        return {
            "result": FixResult.SUCCESS if removed_count > 0 else FixResult.NOT_APPLICABLE,
            "message": f"Removed {removed_count} unused material(s)",
            "details": {"materials_removed": removed_count}
        }

    def _fix_add_basic_lighting(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Add basic three-point lighting setup"""

        # Check if lights already exist
        existing_lights = [obj for obj in context.scene.objects if obj.type == 'LIGHT']

        if existing_lights:
            return {"result": FixResult.NOT_APPLICABLE, "message": "Scene already has lighting"}

        try:
            # Add key light (Sun)
            bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
            key_light = bpy.context.active_object
            key_light.name = "BlendPro_Key_Light"
            key_light.data.energy = 3.0

            # Add fill light (Area)
            bpy.ops.object.light_add(type='AREA', location=(-3, -3, 4))
            fill_light = bpy.context.active_object
            fill_light.name = "BlendPro_Fill_Light"
            fill_light.data.energy = 1.5
            fill_light.data.size = 2.0

            # Add rim light (Spot)
            bpy.ops.object.light_add(type='SPOT', location=(0, 5, 6))
            rim_light = bpy.context.active_object
            rim_light.name = "BlendPro_Rim_Light"
            rim_light.data.energy = 2.0
            rim_light.data.spot_size = 1.2

            return {
                "result": FixResult.SUCCESS,
                "message": "Added three-point lighting setup",
                "details": {"lights_added": 3}
            }

        except Exception as e:
            return {"result": FixResult.FAILED, "message": f"Failed to add lighting: {str(e)}"}

    def _fix_normalize_light_energy(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Normalize overly bright lights"""

        lights = [obj for obj in context.scene.objects if obj.type == 'LIGHT']

        if not lights:
            return {"result": FixResult.NOT_APPLICABLE, "message": "No lights in scene"}

        normalized_count = 0
        max_energy = 10.0  # Maximum reasonable energy

        for light in lights:
            if light.data.energy > max_energy:
                try:
                    light.data.energy = max_energy
                    normalized_count += 1
                except Exception as e:
                    print(f"Failed to normalize light {light.name}: {e}")
                    continue

        return {
            "result": FixResult.SUCCESS if normalized_count > 0 else FixResult.NOT_APPLICABLE,
            "message": f"Normalized energy for {normalized_count} light(s)",
            "details": {"lights_normalized": normalized_count}
        }

    def _fix_set_active_camera(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Set active camera or create one if none exists"""

        # Check if active camera already exists
        if context.scene.camera:
            return {"result": FixResult.NOT_APPLICABLE, "message": "Active camera already set"}

        # Find existing cameras
        cameras = [obj for obj in context.scene.objects if obj.type == 'CAMERA']

        if cameras:
            # Set first camera as active
            context.scene.camera = cameras[0]
            return {
                "result": FixResult.SUCCESS,
                "message": f"Set '{cameras[0].name}' as active camera",
                "details": {"camera_name": cameras[0].name}
            }
        else:
            # Create new camera
            try:
                bpy.ops.object.camera_add(location=(7, -7, 5))
                camera = bpy.context.active_object
                camera.name = "BlendPro_Camera"
                context.scene.camera = camera

                return {
                    "result": FixResult.SUCCESS,
                    "message": "Created and set new active camera",
                    "details": {"camera_name": camera.name}
                }

            except Exception as e:
                return {"result": FixResult.FAILED, "message": f"Failed to create camera: {str(e)}"}

    def _fix_add_decimate_modifiers(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Add decimate modifiers to high-polygon objects"""

        objects_to_fix = self._get_target_mesh_objects(context, target_objects)
        high_poly_threshold = 50000

        high_poly_objects = []
        for obj in objects_to_fix:
            if hasattr(obj.data, 'vertices') and len(obj.data.vertices) > high_poly_threshold:
                high_poly_objects.append(obj)

        if not high_poly_objects:
            return {"result": FixResult.NOT_APPLICABLE, "message": "No high-polygon objects found"}

        modified_count = 0

        for obj in high_poly_objects:
            try:
                # Check if decimate modifier already exists
                if "BlendPro_Decimate" not in [mod.name for mod in obj.modifiers]:
                    mod = obj.modifiers.new('BlendPro_Decimate', 'DECIMATE')
                    mod.ratio = 0.5  # Reduce by 50%
                    mod.use_collapse_triangulate = True
                    modified_count += 1

            except Exception as e:
                print(f"Failed to add decimate modifier to {obj.name}: {e}")
                continue

        return {
            "result": FixResult.SUCCESS if modified_count > 0 else FixResult.FAILED,
            "message": f"Added decimate modifiers to {modified_count} object(s)",
            "details": {"objects_modified": modified_count}
        }

    def _fix_rename_default_objects(self, context, target_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Rename objects with default names"""

        objects_to_fix = target_objects or [obj.name for obj in context.scene.objects]
        default_patterns = ["Cube", "Sphere", "Cylinder", "Plane", "Torus", "Suzanne"]

        renamed_count = 0

        for obj_name in objects_to_fix:
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                continue

            # Check if object has default name
            base_name = obj.name.split('.')[0]  # Remove .001, .002 etc.

            if base_name in default_patterns:
                try:
                    # Generate descriptive name based on object type and properties
                    new_name = self._generate_descriptive_name(obj)
                    obj.name = new_name
                    renamed_count += 1

                except Exception as e:
                    print(f"Failed to rename object {obj.name}: {e}")
                    continue

        return {
            "result": FixResult.SUCCESS if renamed_count > 0 else FixResult.NOT_APPLICABLE,
            "message": f"Renamed {renamed_count} object(s) with descriptive names",
            "details": {"objects_renamed": renamed_count}
        }

    def _generate_descriptive_name(self, obj) -> str:
        """Generate descriptive name for object"""

        base_type = obj.type.lower()

        # Add material info if available
        material_suffix = ""
        if obj.material_slots and obj.material_slots[0].material:
            mat_name = obj.material_slots[0].material.name
            if not mat_name.startswith("Material"):
                material_suffix = f"_{mat_name}"

        # Add size info for mesh objects
        size_suffix = ""
        if obj.type == 'MESH' and hasattr(obj, 'dimensions'):
            max_dim = max(obj.dimensions)
            if max_dim > 10:
                size_suffix = "_Large"
            elif max_dim < 1:
                size_suffix = "_Small"

        return f"{base_type.capitalize()}{material_suffix}{size_suffix}"

    def _get_target_mesh_objects(self, context, target_objects: Optional[List[str]] = None):
        """Get mesh objects to operate on"""

        if target_objects:
            objects = [bpy.data.objects.get(name) for name in target_objects]
            objects = [obj for obj in objects if obj and obj.type == 'MESH']
        else:
            objects = [obj for obj in context.scene.objects if obj.type == 'MESH']

        return objects

    def get_available_fixes(self) -> List[Dict[str, Any]]:
        """Get all available fixes"""

        return [
            {
                "fix_id": fix.fix_id,
                "name": fix.name,
                "description": fix.description,
                "categories": fix.applicable_categories,
                "severities": [s.value for s in fix.applicable_severities],
                "batch_capable": fix.batch_capable,
                "requires_backup": fix.requires_backup
            }
            for fix in self._fixes.values()
        ]

    def get_fix_stats(self) -> Dict[str, Any]:
        """Get auto-fix system statistics"""

        return {
            "total_fixes": len(self._fixes),
            "batch_capable_fixes": sum(1 for fix in self._fixes.values() if fix.batch_capable),
            "backup_required_fixes": sum(1 for fix in self._fixes.values() if fix.requires_backup),
            "categories": list(set(cat for fix in self._fixes.values() for cat in fix.applicable_categories))
        }

# Blender operators for auto-fix system
class BLENDPRO_OT_AutoFixScene(bpy.types.Operator):
    """Automatically fix common scene issues"""
    bl_idname = "blendpro.auto_fix_scene"
    bl_label = "Auto-Fix Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        auto_fix_system = get_auto_fix_system()
        result = auto_fix_system.auto_fix_scene(context)

        if result.get("error"):
            self.report({'ERROR'}, result["error"])
            return {'CANCELLED'}

        message = result.get("message", "Auto-fix completed")
        fixes_applied = result.get("fixes_applied", 0)

        if fixes_applied > 0:
            self.report({'INFO'}, message)
        else:
            self.report({'INFO'}, "No issues found that can be auto-fixed")

        return {'FINISHED'}

class BLENDPRO_OT_ApplySpecificFix(bpy.types.Operator):
    """Apply a specific auto-fix"""
    bl_idname = "blendpro.apply_specific_fix"
    bl_label = "Apply Fix"
    bl_options = {'REGISTER', 'UNDO'}

    fix_id: bpy.props.StringProperty()

    def execute(self, context):
        if not self.fix_id:
            self.report({'ERROR'}, "No fix ID specified")
            return {'CANCELLED'}

        auto_fix_system = get_auto_fix_system()
        result = auto_fix_system.apply_fix(self.fix_id, context)

        if result.get("result") == FixResult.SUCCESS:
            self.report({'INFO'}, result.get("message", "Fix applied successfully"))
        elif result.get("result") == FixResult.NOT_APPLICABLE:
            self.report({'INFO'}, result.get("message", "Fix not applicable"))
        else:
            error_msg = result.get("error", result.get("message", "Fix failed"))
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}

        return {'FINISHED'}

# Global auto-fix system instance
_auto_fix_system: Optional[AutoFixSystem] = None

def get_auto_fix_system() -> AutoFixSystem:
    """Get global auto-fix system instance"""
    global _auto_fix_system
    if _auto_fix_system is None:
        _auto_fix_system = AutoFixSystem()
    return _auto_fix_system

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_OT_AutoFixScene)
    bpy.utils.register_class(BLENDPRO_OT_ApplySpecificFix)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_ApplySpecificFix)
    bpy.utils.unregister_class(BLENDPRO_OT_AutoFixScene)
