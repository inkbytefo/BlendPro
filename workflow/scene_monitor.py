"""
Scene Health Monitor for BlendPro: AI Co-Pilot
Real-time scene monitoring and health analysis
"""

import bpy
import bmesh
import time
import threading
import hashlib
from typing import Dict, List, Any, Optional, Callable
from collections import deque
from dataclasses import dataclass
from enum import Enum

from ..config.settings import get_settings
from ..config.prompts import get_system_prompt, PromptType
from ..utils.api_client import get_api_client, APIRequest
from ..vision.scene_analyzer import get_scene_analyzer

class IssueSeverity(Enum):
    """Severity levels for scene issues"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    SUGGESTION = "SUGGESTION"

@dataclass
class SceneIssue:
    """Represents a scene issue"""
    severity: IssueSeverity
    category: str
    description: str
    affected_objects: List[str]
    fix_suggestion: str
    auto_fixable: bool = False
    fix_code: Optional[str] = None

class SceneHealthMonitor:
    """Monitors scene health and provides proactive suggestions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_client = get_api_client()
        self.scene_analyzer = get_scene_analyzer()
        
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._last_scene_hash = None
        self._last_analysis_time = 0
        self._issue_history: deque = deque(maxlen=100)
        self._suggestions_queue: deque = deque(maxlen=20)
        
        # Health check functions
        self._health_checks = [
            self._check_geometry_issues,
            self._check_material_issues,
            self._check_lighting_setup,
            self._check_performance_issues,
            self._check_organization_issues,
            self._check_render_settings
        ]
    
    def start_monitoring(self, context) -> bool:
        """Start real-time scene monitoring"""
        
        if self._monitoring_active:
            return True
        
        if not self.settings.enable_scene_monitoring:
            return False
        
        try:
            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(context,),
                daemon=True
            )
            self._monitoring_thread.start()
            return True
            
        except Exception as e:
            print(f"Failed to start scene monitoring: {e}")
            self._monitoring_active = False
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop scene monitoring"""
        
        self._monitoring_active = False
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2.0)
        
        return True
    
    def _monitoring_loop(self, context):
        """Main monitoring loop"""
        
        while self._monitoring_active:
            try:
                # Check if scene has changed
                current_hash = self._calculate_scene_hash(context)
                
                if (current_hash != self._last_scene_hash and 
                    time.time() - self._last_analysis_time > self.settings.analysis_cooldown):
                    
                    # Perform health analysis
                    health_report = self.analyze_scene_health(context)
                    
                    if not health_report.get("error"):
                        self._process_health_report(health_report)
                    
                    self._last_scene_hash = current_hash
                    self._last_analysis_time = time.time()
                
                # Sleep for monitoring interval
                time.sleep(self.settings.monitoring_interval)
                
            except Exception as e:
                print(f"Scene monitoring error: {e}")
                time.sleep(5.0)  # Longer sleep on error
    
    def analyze_scene_health(self, context) -> Dict[str, Any]:
        """Perform comprehensive scene health analysis"""
        
        try:
            analysis_start = time.time()
            
            # Get scene data
            scene_data = self.scene_analyzer.analyze_scene(context)
            
            if scene_data.get("error"):
                return {"error": scene_data["error"]}
            
            # Run all health checks
            all_issues = []
            
            for health_check in self._health_checks:
                try:
                    issues = health_check(scene_data, context)
                    all_issues.extend(issues)
                except Exception as e:
                    print(f"Health check error: {e}")
                    continue
            
            # Calculate overall health score
            overall_score = self._calculate_health_score(all_issues)
            
            # Categorize issues
            critical_issues = [i for i in all_issues if i.severity == IssueSeverity.CRITICAL]
            warnings = [i for i in all_issues if i.severity == IssueSeverity.WARNING]
            suggestions = [i for i in all_issues if i.severity == IssueSeverity.SUGGESTION]
            
            # Generate AI-powered insights if enabled
            ai_insights = None
            if len(all_issues) > 0:
                ai_insights = self._generate_ai_insights(scene_data, all_issues)
            
            health_report = {
                "overall_score": overall_score,
                "issues": [self._issue_to_dict(issue) for issue in all_issues],
                "critical_count": len(critical_issues),
                "warning_count": len(warnings),
                "suggestion_count": len(suggestions),
                "analysis_time": time.time() - analysis_start,
                "ai_insights": ai_insights,
                "timestamp": time.time()
            }
            
            return health_report
            
        except Exception as e:
            return {"error": f"Health analysis failed: {str(e)}"}
    
    def _check_geometry_issues(self, scene_data: Dict[str, Any], context) -> List[SceneIssue]:
        """Check for geometry-related issues"""
        
        issues = []
        
        for obj_data in scene_data.get("objects", []):
            if obj_data["type"] != "MESH":
                continue
            
            obj_name = obj_data["name"]
            
            # Check for high polygon count
            vertices = obj_data.get("vertices", 0)
            if vertices > 100000:
                issues.append(SceneIssue(
                    severity=IssueSeverity.WARNING,
                    category="geometry",
                    description=f"High polygon count: {vertices:,} vertices",
                    affected_objects=[obj_name],
                    fix_suggestion="Consider using a Decimate modifier to reduce polygon count",
                    auto_fixable=True,
                    fix_code=f"""
import bpy
obj = bpy.data.objects['{obj_name}']
mod = obj.modifiers.new('Decimate', 'DECIMATE')
mod.ratio = 0.5
"""
                ))
            
            # Check for mesh issues
            mesh_issues = obj_data.get("issues", [])
            for issue in mesh_issues:
                if "Non-manifold" in issue:
                    issues.append(SceneIssue(
                        severity=IssueSeverity.WARNING,
                        category="geometry",
                        description=f"Non-manifold geometry detected: {issue}",
                        affected_objects=[obj_name],
                        fix_suggestion="Use Mesh > Clean Up > Make Manifold or manually fix geometry",
                        auto_fixable=True,
                        fix_code=f"""
import bpy
import bmesh
obj = bpy.data.objects['{obj_name}']
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles()
bpy.ops.object.mode_set(mode='OBJECT')
"""
                    ))
                
                elif "Loose vertices" in issue:
                    issues.append(SceneIssue(
                        severity=IssueSeverity.INFO,
                        category="geometry",
                        description=f"Loose vertices found: {issue}",
                        affected_objects=[obj_name],
                        fix_suggestion="Remove loose vertices using Mesh > Clean Up > Delete Loose",
                        auto_fixable=True,
                        fix_code=f"""
import bpy
obj = bpy.data.objects['{obj_name}']
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.select_loose()
bpy.ops.mesh.delete(type='VERT')
bpy.ops.object.mode_set(mode='OBJECT')
"""
                    ))
        
        return issues
    
    def _check_material_issues(self, scene_data: Dict[str, Any], context) -> List[SceneIssue]:
        """Check for material-related issues"""
        
        issues = []
        materials = scene_data.get("materials", [])
        
        # Check for objects without materials
        objects_without_materials = []
        for obj_data in scene_data.get("objects", []):
            if obj_data["type"] == "MESH" and obj_data.get("material_slots", 0) == 0:
                objects_without_materials.append(obj_data["name"])
        
        if objects_without_materials:
            issues.append(SceneIssue(
                severity=IssueSeverity.INFO,
                category="materials",
                description=f"{len(objects_without_materials)} objects without materials",
                affected_objects=objects_without_materials,
                fix_suggestion="Assign materials to improve visual quality",
                auto_fixable=True,
                fix_code=f"""
import bpy
# Create a basic material
mat = bpy.data.materials.new(name="Basic_Material")
mat.use_nodes = True

# Assign to objects without materials
for obj_name in {objects_without_materials}:
    obj = bpy.data.objects.get(obj_name)
    if obj and obj.type == 'MESH':
        if len(obj.material_slots) == 0:
            obj.data.materials.append(mat)
        else:
            obj.material_slots[0].material = mat
"""
            ))
        
        # Check for unused materials
        unused_materials = [mat for mat in materials if mat.get("users", 0) == 0]
        if unused_materials:
            issues.append(SceneIssue(
                severity=IssueSeverity.INFO,
                category="materials",
                description=f"{len(unused_materials)} unused materials",
                affected_objects=[mat["name"] for mat in unused_materials],
                fix_suggestion="Remove unused materials to clean up the scene",
                auto_fixable=True,
                fix_code="""
import bpy
for mat in bpy.data.materials:
    if mat.users == 0:
        bpy.data.materials.remove(mat)
"""
            ))
        
        return issues
    
    def _check_lighting_setup(self, scene_data: Dict[str, Any], context) -> List[SceneIssue]:
        """Check lighting setup"""
        
        issues = []
        lights = scene_data.get("lights", [])
        
        # Check if scene has no lights
        if not lights:
            issues.append(SceneIssue(
                severity=IssueSeverity.WARNING,
                category="lighting",
                description="No lights in scene",
                affected_objects=[],
                fix_suggestion="Add at least one light source for proper illumination",
                auto_fixable=True,
                fix_code="""
import bpy
# Add a sun light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
light = bpy.context.active_object
light.data.energy = 3.0
light.name = "Main_Sun"
"""
            ))
        
        # Check for very high energy lights
        high_energy_lights = []
        for light in lights:
            if light.get("energy", 0) > 1000:
                high_energy_lights.append(light["name"])
        
        if high_energy_lights:
            issues.append(SceneIssue(
                severity=IssueSeverity.WARNING,
                category="lighting",
                description=f"Very high energy lights detected",
                affected_objects=high_energy_lights,
                fix_suggestion="Consider reducing light energy for more realistic lighting",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_performance_issues(self, scene_data: Dict[str, Any], context) -> List[SceneIssue]:
        """Check for performance-related issues"""
        
        issues = []
        objects = scene_data.get("objects", [])
        
        # Check total object count
        if len(objects) > 1000:
            issues.append(SceneIssue(
                severity=IssueSeverity.WARNING,
                category="performance",
                description=f"High object count: {len(objects)} objects",
                affected_objects=[],
                fix_suggestion="Consider using collections and instancing to optimize performance",
                auto_fixable=False
            ))
        
        # Check for objects with many modifiers
        heavy_modifier_objects = []
        for obj_data in objects:
            modifier_count = len(obj_data.get("modifiers", []))
            if modifier_count > 5:
                heavy_modifier_objects.append(obj_data["name"])
        
        if heavy_modifier_objects:
            issues.append(SceneIssue(
                severity=IssueSeverity.INFO,
                category="performance",
                description=f"Objects with many modifiers: {len(heavy_modifier_objects)}",
                affected_objects=heavy_modifier_objects,
                fix_suggestion="Consider applying modifiers or optimizing modifier stack",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_organization_issues(self, scene_data: Dict[str, Any], context) -> List[SceneIssue]:
        """Check scene organization"""
        
        issues = []
        objects = scene_data.get("objects", [])
        
        # Check for default names
        default_named_objects = []
        for obj_data in objects:
            name = obj_data["name"]
            if any(default in name for default in ["Cube", "Sphere", "Cylinder", "Plane"]):
                if name.endswith((".001", ".002", ".003")) or name in ["Cube", "Sphere", "Cylinder", "Plane"]:
                    default_named_objects.append(name)
        
        if default_named_objects:
            issues.append(SceneIssue(
                severity=IssueSeverity.SUGGESTION,
                category="organization",
                description=f"{len(default_named_objects)} objects with default names",
                affected_objects=default_named_objects,
                fix_suggestion="Rename objects with descriptive names for better organization",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_render_settings(self, scene_data: Dict[str, Any], context) -> List[SceneIssue]:
        """Check render settings"""
        
        issues = []
        render_settings = scene_data.get("render_settings", {})
        cameras = scene_data.get("cameras", [])
        
        # Check if no active camera
        active_cameras = [cam for cam in cameras if cam.get("is_active", False)]
        if not active_cameras:
            issues.append(SceneIssue(
                severity=IssueSeverity.WARNING,
                category="render",
                description="No active camera set",
                affected_objects=[],
                fix_suggestion="Set an active camera for rendering",
                auto_fixable=True,
                fix_code="""
import bpy
# Find first camera or create one
camera = None
for obj in bpy.context.scene.objects:
    if obj.type == 'CAMERA':
        camera = obj
        break

if not camera:
    bpy.ops.object.camera_add(location=(7, -7, 5))
    camera = bpy.context.active_object

bpy.context.scene.camera = camera
"""
            ))
        
        # Check resolution
        res_x = render_settings.get("resolution_x", 1920)
        res_y = render_settings.get("resolution_y", 1080)
        
        if res_x * res_y > 4000000:  # 4K+
            issues.append(SceneIssue(
                severity=IssueSeverity.INFO,
                category="render",
                description=f"High render resolution: {res_x}x{res_y}",
                affected_objects=[],
                fix_suggestion="High resolution may increase render times significantly",
                auto_fixable=False
            ))
        
        return issues

    def _calculate_health_score(self, issues: List[SceneIssue]) -> float:
        """Calculate overall health score (0-100)"""

        if not issues:
            return 100.0

        # Weight different severity levels
        severity_weights = {
            IssueSeverity.CRITICAL: -25,
            IssueSeverity.WARNING: -10,
            IssueSeverity.INFO: -3,
            IssueSeverity.SUGGESTION: -1
        }

        total_penalty = sum(severity_weights.get(issue.severity, 0) for issue in issues)
        score = max(0, 100 + total_penalty)

        return score

    def _generate_ai_insights(self, scene_data: Dict[str, Any], issues: List[SceneIssue]) -> Optional[str]:
        """Generate AI-powered insights about scene health"""

        try:
            # Prepare issues summary
            issues_summary = []
            for issue in issues[:10]:  # Limit to top 10 issues
                issues_summary.append({
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "description": issue.description,
                    "affected_objects": issue.affected_objects[:5]  # Limit objects
                })

            system_prompt = get_system_prompt(
                PromptType.SCENE_HEALTH,
                scene_data=str(scene_data.get("metadata", {}))
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze these scene health issues and provide insights: {issues_summary}"}
            ]

            request = APIRequest(
                messages=messages,
                model="gpt-4o-mini",  # Use fast model for insights
                temperature=0.3,
                max_tokens=300
            )

            response = self.api_client.make_request(request)

            if not response.error:
                return response.content

        except Exception as e:
            print(f"AI insights generation failed: {e}")

        return None

    def _calculate_scene_hash(self, context) -> str:
        """Calculate hash representing current scene state"""

        try:
            scene_signature = []

            # Basic scene info
            scene = context.scene
            scene_signature.append(f"frame:{scene.frame_current}")
            scene_signature.append(f"engine:{scene.render.engine}")

            # Object signatures (simplified)
            for obj in context.scene.objects:
                if obj.visible_get():
                    obj_sig = f"{obj.name}_{obj.type}_{len(obj.modifiers)}"
                    scene_signature.append(obj_sig)

            # Create hash
            combined_signature = "|".join(sorted(scene_signature))
            return hashlib.md5(combined_signature.encode()).hexdigest()

        except Exception:
            return str(time.time())  # Fallback to timestamp

    def _process_health_report(self, health_report: Dict[str, Any]) -> None:
        """Process health report and generate suggestions"""

        # Add to history
        self._issue_history.append(health_report)

        # Generate suggestions for critical and warning issues
        issues = health_report.get("issues", [])
        critical_and_warnings = [
            issue for issue in issues
            if issue.get("severity") in ["CRITICAL", "WARNING"]
        ]

        if critical_and_warnings:
            suggestion = {
                "timestamp": time.time(),
                "type": "health_alert",
                "message": f"Found {len(critical_and_warnings)} important issues in your scene",
                "issues": critical_and_warnings[:3],  # Top 3 issues
                "overall_score": health_report.get("overall_score", 0)
            }

            self._suggestions_queue.append(suggestion)

    def _issue_to_dict(self, issue: SceneIssue) -> Dict[str, Any]:
        """Convert SceneIssue to dictionary"""

        return {
            "severity": issue.severity.value,
            "category": issue.category,
            "description": issue.description,
            "affected_objects": issue.affected_objects,
            "fix_suggestion": issue.fix_suggestion,
            "auto_fixable": issue.auto_fixable,
            "fix_code": issue.fix_code
        }

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""

        return {
            "active": self._monitoring_active,
            "enabled": self.settings.enable_scene_monitoring,
            "interval": self.settings.monitoring_interval,
            "last_analysis": self._last_analysis_time,
            "issue_history_count": len(self._issue_history),
            "suggestions_count": len(self._suggestions_queue)
        }

    def get_recent_suggestions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent proactive suggestions"""

        return list(self._suggestions_queue)[-limit:]

    def clear_suggestions(self) -> None:
        """Clear suggestions queue"""

        self._suggestions_queue.clear()

    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health analysis history"""

        return list(self._issue_history)[-limit:]

# Blender operators for scene monitoring
class BLENDPRO_OT_ToggleSceneMonitoring(bpy.types.Operator):
    """Toggle scene monitoring on/off"""
    bl_idname = "blendpro.toggle_scene_monitoring"
    bl_label = "Toggle Scene Monitoring"
    bl_options = {'REGISTER'}

    def execute(self, context):
        monitor = get_scene_health_monitor()
        status = monitor.get_monitoring_status()

        if status["active"]:
            success = monitor.stop_monitoring()
            if success:
                self.report({'INFO'}, "Scene monitoring stopped")
                context.scene.blendpro_monitoring_active = False
            else:
                self.report({'ERROR'}, "Failed to stop monitoring")
        else:
            success = monitor.start_monitoring(context)
            if success:
                self.report({'INFO'}, "Scene monitoring started")
                context.scene.blendpro_monitoring_active = True
            else:
                self.report({'ERROR'}, "Failed to start monitoring")

        return {'FINISHED'}

class BLENDPRO_OT_AnalyzeSceneHealth(bpy.types.Operator):
    """Perform immediate scene health analysis"""
    bl_idname = "blendpro.analyze_scene_health"
    bl_label = "Analyze Scene Health"
    bl_options = {'REGISTER'}

    def execute(self, context):
        monitor = get_scene_health_monitor()
        health_report = monitor.analyze_scene_health(context)

        if health_report.get("error"):
            self.report({'ERROR'}, f"Analysis failed: {health_report['error']}")
            return {'CANCELLED'}

        # Report results
        overall_score = health_report.get("overall_score", 0)
        issues_count = len(health_report.get("issues", []))

        if overall_score >= 80:
            self.report({'INFO'}, f"Scene health: Excellent ({overall_score:.0f}/100)")
        elif overall_score >= 60:
            self.report({'INFO'}, f"Scene health: Good ({overall_score:.0f}/100)")
        elif overall_score >= 40:
            self.report({'WARNING'}, f"Scene health: Fair ({overall_score:.0f}/100) - {issues_count} issues")
        else:
            self.report({'ERROR'}, f"Scene health: Poor ({overall_score:.0f}/100) - {issues_count} issues")

        # Print detailed results to console
        print("\n" + "="*50)
        print("SCENE HEALTH ANALYSIS REPORT")
        print("="*50)
        print(f"Overall Score: {overall_score:.1f}/100")

        issues = health_report.get("issues", [])
        if issues:
            print(f"\nISSUES ({len(issues)}):")
            for i, issue in enumerate(issues[:10], 1):
                print(f"  {i}. [{issue['severity']}] {issue['description']}")

        ai_insights = health_report.get("ai_insights")
        if ai_insights:
            print(f"\nAI INSIGHTS:")
            print(f"  {ai_insights}")

        print("="*50)

        return {'FINISHED'}

# Global scene health monitor instance
_scene_health_monitor: Optional[SceneHealthMonitor] = None

def get_scene_health_monitor() -> SceneHealthMonitor:
    """Get global scene health monitor instance"""
    global _scene_health_monitor
    if _scene_health_monitor is None:
        _scene_health_monitor = SceneHealthMonitor()
    return _scene_health_monitor

def register():
    """Register Blender classes"""
    bpy.utils.register_class(BLENDPRO_OT_ToggleSceneMonitoring)
    bpy.utils.register_class(BLENDPRO_OT_AnalyzeSceneHealth)

def unregister():
    """Unregister Blender classes"""
    bpy.utils.unregister_class(BLENDPRO_OT_AnalyzeSceneHealth)
    bpy.utils.unregister_class(BLENDPRO_OT_ToggleSceneMonitoring)
