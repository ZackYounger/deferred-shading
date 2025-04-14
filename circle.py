import pygame
import math

# Initialize Pygame
pygame.init()

# Create a 16x16 surface with alpha
size = 100
surface = pygame.Surface((size, size), pygame.SRCALPHA)
center = size / 2
radius = size / 2

# Generate the normal map
for x in range(size):
    for y in range(size):
        dx = x - center
        dy = y - center
        dist = math.sqrt(dx*dx + dy*dy)
        if dist <= radius and dist >= 0:



            #normal = (dx/dist, dy/dist)  # Normalized direction vector
            # Map normal [-1, 1] to [0, 1] for RG channels
            r = int(255 * x / size)  # Red: 0 (left) to 1 (right)
            g = int(255 * y / size)  # Green: 0 (top) to 1 (bottom)
            surface.set_at((x, y), (255, 255, 255, 255))  # Blue=0, Alpha=255
        else:
            surface.set_at((x, y), (128, 128, 0, 0))  # Neutral normal, transparent

# Save the normal map
pygame.image.save(surface, "sphere.png")

# Quit Pygame
pygame.quit()
