import sys
from array import array
import pygame
import moderngl
import math


from light import PointLight

pygame.init()

# janky aah maths setup
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)

pixel_size = 3 # 4 for full hd, 8 for 4k

display_width, display_height = 480, 270
screen_width, screen_height = display_width * pixel_size, display_height * pixel_size

print(f'screen size of {screen_width} x {screen_height}')

screen = pygame.display.set_mode((screen_width, screen_height), pygame.OPENGL | pygame.DOUBLEBUF)
display = pygame.Surface((display_width, display_height))
color_buffer = pygame.Surface((display_width, display_height))
normal_buffer = pygame.Surface((display_width, display_height))


ctx = moderngl.create_context(require=330)
clock = pygame.time.Clock()

# Full-screen quad
full_quad_buffer = ctx.buffer(data=array('f', [
    -1.0, 1.0, 0.0, 0.0,
    1.0, 1.0, 1.0, 0.0,
    -1.0, -1.0, 0.0, 1.0,
    1.0, -1.0, 1.0, 1.0,
]))

# Scene shaders
vert_shader_scene = '''
#version 330 core
in vec2 vert;
in vec2 texcoord;
out vec2 uvs;
void main() {
    uvs = texcoord;
    gl_Position = vec4(vert, 0.0, 1.0);
}
'''

frag_shader_scene = '''
#version 330 core
uniform sampler2D tex;
in vec2 uvs;
out vec4 f_color;
void main() {
    f_color = texture(tex, uvs);
}
'''



# Upscale shaders
vert_shader_upscale = '''
#version 330 core
in vec2 vert;
in vec2 texcoord;
out vec2 uvs;
void main() {
    uvs = texcoord;
    gl_Position = vec4(vert, 0.0, 1.0);
}
'''

frag_shader_upscale = '''
#version 330 core
uniform sampler2D tex;
in vec2 uvs;
out vec4 f_color;
void main() {
    f_color = texture(tex, uvs);
}
'''

# Compile shaders
try:
    program_scene = ctx.program(vertex_shader=vert_shader_scene, fragment_shader=frag_shader_scene)
    program_upscale = ctx.program(vertex_shader=vert_shader_upscale, fragment_shader=frag_shader_upscale)
except Exception as e:
    print(f"Shader compilation error: {e}")
    sys.exit(1)

# Vertex arrays
render_object_scene = ctx.vertex_array(program_scene, [(full_quad_buffer, '2f 2f', 'vert', 'texcoord')])
render_object_upscale = ctx.vertex_array(program_upscale, [(full_quad_buffer, '2f 2f', 'vert', 'texcoord')])

# Framebuffer
fbo_texture = ctx.texture(display.get_size(), 4)
fbo_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
fbo = ctx.framebuffer(color_attachments=[fbo_texture])

normal_fbo_texture = ctx.texture((display_width, display_height), 4)  # 32x24 normals
normal_fbo_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
normal_fbo = ctx.framebuffer(color_attachments=[normal_fbo_texture])

color_fbo_texture = ctx.texture((display_width, display_height), 4)  # 32x24 normals
color_fbo_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
color_fbo = ctx.framebuffer(color_attachments=[color_fbo_texture])

def surf_to_texture(surf):
    tex = ctx.texture(surf.get_size(), 4)
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    tex.swizzle = 'BGRA'
    tex.write(surf.get_view('1'))
    return tex

# Precompute sphere normal map
# normal_map = create_sphere_normal_map(size=16)

size = 30

sphere_color_sprite = pygame.image.load("sphere.png")
sphere_color_sprite = pygame.transform.scale(sphere_color_sprite, (size,size))

sphere_normal_sprite = pygame.image.load("sphere_normal.png")
sphere_normal_sprite = pygame.transform.scale(sphere_normal_sprite, (size,size))

# Light over rectangle
light = PointLight(ctx=ctx, x=140, y=130, radius=150, color=(1.0, 0.75, 0.5), intensity=2, volumetric_intensity=.3,angle=0,angular_width=.6)
light2 = PointLight(ctx=ctx, x=140, y=130, radius=150, color=(1.0, 0.75, 0.5), intensity=2, volumetric_intensity=.3,angle=3.14,angular_width=.6)

font = pygame.font.SysFont("arial", 24)

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    light2.angle += .01

    display.fill((0, 0, 0))  # Clear low-res surface
    color_buffer.fill((0, 0, 0))  # Clear low-res surface
    normal_buffer.fill((0, 0, 255, 0))  # Clear low-res surface

    #normal_buffer.fill((128, 128, 0, 0))  # Clear normals to (0, 0)
    #color_buffer.fill((128, 128, 0, 0))  # Clear normals to (0, 0)

    mspt = clock.get_time()
    #mspt_text = font.render(f"MSPT: {mspt} ms", True, (255, 255, 255))
    #color_buffer.blit(mspt_text, (10, 10))
    #print(mspt)

    # Blit sprite color and normals
    sprite_pos = (180, 100)  # Center at ~16,12 in 32x24
    color_buffer.blit(sphere_color_sprite, (sprite_pos[0], sprite_pos[1]))
    normal_buffer.blit(sphere_normal_sprite, (sprite_pos[0], sprite_pos[1]))

    # First pass

    color_fbo.use()
    color_fbo.clear(0.0, 0.0, 0.0, 1.0)
    color_tex = surf_to_texture(color_buffer)
    color_tex.use(0)
    program_scene['tex'] = 0
    render_object_scene.render(mode=moderngl.TRIANGLE_STRIP)
    color_tex.release()


    normal_fbo.use()
    normal_fbo.clear(0.0, 0.0, 1.0, 0.0)
    normal_tex = surf_to_texture(normal_buffer)
    normal_tex.use(0)
    program_scene['tex'] = 0
    render_object_scene.render(mode=moderngl.TRIANGLE_STRIP)
    normal_tex.release()


    # bind color and normal buffers for light pass
    color_fbo_texture.use(0)
    normal_fbo_texture.use(1)
    light.program['color_tex'] = 0
    light.program['normal_tex'] = 1


    # Second pass: Apply light shader to fbo
    fbo.use()
    fbo.clear(0.0, 0.0, 0.0, 1.0)
    light.render(ctx)

    
    fbo.use()
    light2.render(ctx)
    

    pygame.image.save(normal_buffer, "normal.png")
    pygame.image.save(color_buffer, "color.png")


    # Debug: Save framebuffer
    pixels = fbo.read(components=4)
    pygame.image.save(pygame.image.fromstring(pixels, (screen_width // pixel_size, screen_height // pixel_size), 'RGBA'), 'fbo_output.png')

    # Second pass: Upscale to 800x600
    ctx.screen.use()
    fbo_texture.use(0)
    program_upscale['tex'] = 0
    render_object_upscale.render(mode=moderngl.TRIANGLE_STRIP)

    pygame.display.flip()
    clock.tick(60)