import moderngl
from array import array
import math

class PointLight:
    def __init__(self, ctx, x, y, radius, color=(1.0, 1.0, 1.0), intensity=1.0, volumetric_intensity=.5, angle=0, angular_width=.4):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity
        self.angle = angle
        self.angular_width = angular_width
        self.volumetric_intensity = volumetric_intensity

        self.program = ctx.program(vertex_shader=vert_shader_light, fragment_shader=frag_shader_light)


    def get_area_of_effect(self):
        x_min = max(0, self.x - self.radius)
        y_min = max(0, self.y - self.radius)
        x_max = min(320, self.x + self.radius)
        y_max = min(240, self.y + self.radius)
        return (x_min, y_min, x_max - x_min, y_max - y_min)

    def get_quad_vertices(self):
        x, y, w, h = self.get_area_of_effect()
        x1 = (x / 320.0) * 2.0 - 1.0
        x2 = ((x + w) / 320.0) * 2.0 - 1.0
        y1 = -((y + h) / 240.0) * 2.0 + 1.0
        y2 = -(y / 240.0) * 2.0 + 1.0
        return array('f', [
            x1, y2, 0.0, 0.0,
            x2, y2, 1.0, 0.0,
            x1, y1, 0.0, 1.0,
            x2, y1, 1.0, 1.0,
        ])

    def render(self, ctx):
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        light_quad_buffer = ctx.buffer(data=self.get_quad_vertices())
        render_object_light = ctx.vertex_array(self.program, [(light_quad_buffer, '2f 2f', 'vert', 'texcoord')])
        self.program['light_tint'] = self.color
        self.program['intensity'] = self.intensity
        self.program['volumetric_intensity'] = self.volumetric_intensity
        self.program['light_dir'] = (math.cos(self.angle), math.sin(self.angle))
        if not self.angular_width:
            self.program['do_angular_falloff'] = 0
        else:
            self.program['do_angular_falloff'] = 1
            self.program['angular_width'] = self.angular_width
        render_object_light.render(mode=moderngl.TRIANGLE_STRIP)
        light_quad_buffer.release()
        ctx.disable(moderngl.BLEND)



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

frag_shader_light = '''
#version 330 core
uniform vec2 light_dir;
uniform float do_angular_falloff;
uniform float angular_width;

uniform vec3 light_tint;
uniform float intensity;
uniform float volumetric_intensity;

uniform sampler2D color_tex;
uniform sampler2D normal_tex;
in vec2 uvs;
out vec4 f_color;
void main() {
    
    vec2 dir_to_light = normalize(vec2(0.5 - uvs.x, uvs.y - 0.5)); //weird upside down fixing
    float dist = distance(vec2(0.5), uvs) * 2;
    float radialFalloff = pow(1 - dist, 2);
    float angularFalloff = do_angular_falloff == 0 ? 1.0 : smoothstep(angular_width, 1.0, dot(light_dir, dir_to_light));

    vec4 normal_sample = texture(normal_tex, uvs);
    vec2 normal = normal_sample.rg * 2.0 - 1.0;
    float normalFalloff = max(0.0, dot(normal, dir_to_light));

    float final_intensity = intensity * radialFalloff * angularFalloff;
    vec3 light_color = light_tint * final_intensity;


    // Use alpha to mask the output
    //if (normal_sample.b == 0) {
        // objects
    vec3 color_sample = texture(color_tex, uvs).rgb;

    f_color = vec4(light_color * color_sample * normalFalloff, 1.0);
        
    //    return;
    //}
    // add volumetric outside

    //f_color = vec4(color_sample * light_color, 1.0);
    f_color += vec4(light_color * volumetric_intensity, 1.0);
    //f_color = vec4(dir_to_light, 0.0, 1.0);
    //f_color = vec4(light_color, 1.0);

}
'''