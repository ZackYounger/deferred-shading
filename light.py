import moderngl
from array import array
import math

class LightingSystem:

    def __init__(self, ctx):

        self.lights = []
        self.global_light = None


        try:
            self.program = ctx.program(vertex_shader=vert_shader_light, fragment_shader=frag_shader_angled_light)
        except Exception as e:
            print(f"Lighting shader compilation error: {e}")
            raise
    

    def addGlobalLight(self, color=(1, .9, .8), intensity=.1):
        self.global_light = self.GlobalLight(color=color, intensity=intensity)

    def addPointLight(self, x, y, radius, color=(1.0, 1.0, 1.0), intensity=1.0, volumetric_intensity=.5, angle=0, angular_width=.4):
        self.lights.append(
            self.PointLight(x, y, radius, color=color, intensity=intensity, volumetric_intensity=volumetric_intensity, angle=angle, angular_width=angular_width)
            )

    def get_quad_vertices(self):
        # Map the full display (480x270) to OpenGL NDC (-1 to 1)
        x1 = -1.0  # Left edge of the screen
        x2 = 1.0   # Right edge of the screen
        y1 = -1.0  # Bottom edge of the screen
        y2 = 1.0   # Top edge of the screen
        return array('f', [
            x1, y2, 0.0, 0.0,  # Top-left
            x2, y2, 1.0, 0.0,  # Top-right
            x1, y1, 0.0, 1.0,  # Bottom-left
            x2, y1, 1.0, 1.0,  # Bottom-right
        ])

    def render(self, ctx):
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        light_quad_buffer = ctx.buffer(data=self.get_quad_vertices())
        render_object_light = ctx.vertex_array(self.program, [(light_quad_buffer, '2f 2f', 'vert', 'texcoord')])

        # pass params

        if self.global_light:
            self.program['global_light_tint'] = self.global_light.color
            self.program['global_intensity'] = self.global_light.intensity
        else:
            self.program['global_light_tint'] = (0, 0, 0)
            self.program['global_intensity'] = 0

        max_point_lights = 10  # Match MAX_POINT_LIGHTS in shader
        
        # Collect light data
        light_pos = [(light.x / 480.0, light.y / 270.0) for light in self.lights]
        light_tint = [light.color for light in self.lights]
        intensity = [light.intensity for light in self.lights]
        volumetric_intensity = [light.volumetric_intensity for light in self.lights]
        light_dir = [(math.cos(light.angle), math.sin(light.angle)) for light in self.lights]
        do_angular_falloff = [1 if light.angular_width else 0 for light in self.lights]
        angular_width = [light.angular_width for light in self.lights]

        # Pad arrays to max_point_lights
        self.program['light_pos'] = light_pos + [(0, 0)] * (max_point_lights - len(self.lights))
        self.program['light_tint'] = light_tint + [(0, 0, 0)] * (max_point_lights - len(self.lights))
        self.program['intensity'] = intensity + [0] * (max_point_lights - len(self.lights))
        self.program['volumetric_intensity'] = volumetric_intensity + [0] * (max_point_lights - len(self.lights))
        self.program['light_dir'] = light_dir + [(0, 0)] * (max_point_lights - len(self.lights))
        self.program['do_angular_falloff'] = do_angular_falloff + [0] * (max_point_lights - len(self.lights))
        self.program['angular_width'] = angular_width + [0] * (max_point_lights - len(self.lights))

        self.program['point_light_count'] = len(self.lights)
        render_object_light.render(mode=moderngl.TRIANGLE_STRIP)
        light_quad_buffer.release()
        ctx.disable(moderngl.BLEND)



    class PointLight:

        def __init__(self, x, y, radius, color=(1.0, 1.0, 1.0), intensity=1.0, volumetric_intensity=.5, angle=0, angular_width=.4):
            self.x = x
            self.y = y
            self.radius = radius
            self.color = color
            self.intensity = intensity
            self.angle = angle
            self.angular_width = angular_width
            self.volumetric_intensity = volumetric_intensity


    class GlobalLight:
        def __init__(self, color=(1.0, 1.0, 1.0), intensity=1.0):
            self.color = color
            self.intensity = intensity





# Light shaders
vert_shader_light = '''
#version 330 core
in vec2 vert;
in vec2 texcoord;
out vec2 uvs;
void main() {
    uvs = texcoord;
    gl_Position = vec4(vert, 0.0, 1.0);
}
'''

frag_shader_angled_light = '''
#version 330 core

#define aspect_ratio 1.777
#define MAX_POINT_LIGHTS 10
#define PI 3.1415

uniform float global_intensity;
uniform vec3 global_light_tint;

uniform vec2 light_dir[MAX_POINT_LIGHTS];
uniform float do_angular_falloff[MAX_POINT_LIGHTS];
uniform float angular_width[MAX_POINT_LIGHTS];

uniform vec3 light_tint[MAX_POINT_LIGHTS];
uniform float intensity[MAX_POINT_LIGHTS];
uniform float volumetric_intensity[MAX_POINT_LIGHTS];

uniform vec2 light_pos[MAX_POINT_LIGHTS];

uniform int point_light_count;

uniform sampler2D color_tex;
uniform sampler2D normal_tex;

in vec2 uvs;
out vec4 f_color;
void main() {
    
    //vec4 f_color = vec4(0);

    vec3 color_sample = texture(color_tex, uvs).rgb;
    vec4 normal_sample = texture(normal_tex, uvs);
    vec2 normal = vec2(normal_sample.r * 2.0 - 1.0, (normal_sample.g * 2.0 - 1.0) * -1.0);

    // Apply global light
    if (global_intensity > 0.0) {
        f_color += vec4(color_sample * global_light_tint * global_intensity, 1.0);
    }

    for (int i = 0; i < point_light_count; i++) {

        // Adjust UV coordinates for aspect ratio
        vec2 adjusted_uvs = vec2(uvs.x, uvs.y * (1.0 / aspect_ratio));
        vec2 adjusted_light_pos = vec2(light_pos[i].x, light_pos[i].y * (1.0 / aspect_ratio));

        vec2 dir_to_light = normalize(adjusted_light_pos - adjusted_uvs);
        float dist = distance(adjusted_light_pos, adjusted_uvs) * 2;
        float radialFalloff = pow(max(0, 1 - dist), 2);
        float angularFalloff = do_angular_falloff[i] == 0 ? 1 : smoothstep(1 - angular_width[i] / PI, 1, dot(light_dir[i], dir_to_light));

        float normalFalloff = max(0.0, dot(normal, dir_to_light));

        float final_intensity = intensity[i] * radialFalloff * angularFalloff;
        vec3 light_color = light_tint[i] * final_intensity;

        // for objects
        f_color += vec4(light_color * color_sample * normalFalloff, 1);

        //add volumetric
        f_color += vec4(light_color * volumetric_intensity[i], 1);

    }

}
'''

frag_shader_global_light = '''
#version 330 core

uniform vec3 light_tint;
uniform float intensity;

uniform sampler2D color_tex;

in vec2 uvs;
out vec4 f_color;
void main() {

    vec3 color_sample = texture(color_tex, uvs).rgb;
    f_color = vec4(color_sample * light_tint * intensity, 0.0);
}
'''