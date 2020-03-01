#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
soap: a useless experiment in pygame

Poke dynamic voronoi cells by left-clicking or create new cells by right-
clicking.
"""
from collections import defaultdict
import numpy as np
from scipy.spatial.qhull import QhullError, Voronoi, Delaunay, ConvexHull
import pygame
import pygame.freetype #For loading font
from pygame.mouse import get_pos as mouse_xy
from pygame.draw import polygon, aalines, circle

# Window dimensions should be at least 670 x 375 to not clip help_menu.
DIM = np.array([800.0, 800.0])
MAX_VEL = 15.0  # Max Velocity of cell centers
NUMBER_OF_CENTERS = 50

def poke_power(poke_loc, center_loc):
    """
    Returns the force vector of a poke.
    """
    difference = center_loc - poke_loc
    distance = np.linalg.norm(difference)
    return 100000 * difference/distance**3 if distance != 0 else 0

class Center:
    """
    Cell center class.  Cell centers have methods that affect their movement.
    """
    def __init__(self, loc):
        self.loc = loc
        self.velocity = np.zeros(2)

    def friction(self):
        """
        Applies friction and limits the magnitude of velocity.

        The friction constant, fric, should satisfy 0 < fric < 1.
        Don't fric it up.
        """
        fric = .97
        self.velocity *= fric
        self.velocity[abs(self.velocity) < .01] = 0.0   #Prevent jitter.
        magnitude = np.linalg.norm(self.velocity)
        if magnitude > MAX_VEL:
            self.velocity *= MAX_VEL / magnitude

    def delta_velocity(self, delta):
        """
        This adds delta to the velocity and then limits the velocity to
        max_vel.
        """
        self.velocity += delta
        magnitude = np.linalg.norm(self.velocity)
        if magnitude > MAX_VEL:
            self.velocity *= MAX_VEL / magnitude

    def move(self):
        """
        Apply velocity to location.
        """
        self.friction()
        self.loc += self.velocity

class Soap:
    """
    The main game functions, and variables, along with the main while loop.
    """
    HELP = ["left-click to poke the centers",
            "right-click to create a new center",
            "w,a,s,d moves the color center",
            "space creates a poke at the color center's location",
            "----------------------------------",
            "Options:",
            "esc -- Toggles this menu",
            "r   -- Reset centers",
            "v   -- Toggle Voronoi dual",
            "b   -- Toggle bouncing (delete out-of-bound centers)",
            "f   -- Toggle fill of Voronoi cells",
            "o   -- Toggle outline of Voronoi cells",
            "h   -- Toggle showing centers of Voronoi cells",
            "up  -- Cycle through color palettes"]

    PALETTES = [lambda color: color,
                lambda color: (color[0], color[0], 255),
                lambda color: (color[0], color[1], 155),
                lambda color: (color[0], color[1], color[1]),
                lambda color: (color[0], color[0], color[0]),
                lambda color: (color[0], color[0], color[2]),
                lambda color: (155, 100, color[0])]

    def __init__(self):
        self.WINDOW = pygame.display.set_mode(DIM.astype(int))
        self.palette = self.PALETTES[0]
        self.keys = defaultdict(bool)

        self.voronoi_dual = False
        self.bouncing = True
        self.fill = True
        self.outline = True
        self.show_help = True
        self.centers_visible = False

        self.running = True

        self.centers = {}
        self.reset() #Randomly place cell centers

        self.color_center = Center(DIM / 2)

    def render_help(self):
        """
        Turns self.HELP into a surface that pygame can blit.
        """
        font = pygame.freetype.Font('NotoSansMono-Regular.ttf', 20)
        self.HELP = [font.render(text, (255, 255, 255)) for text in self.HELP]
        self.HELP = [i for i, _ in self.HELP]

    def move_centers(self):
        """
        Handle behavior of cell center movement at the boundaries. Then
        move each cell center.

        Also handles the manual movement of color center.
        """
        #Movement for cell centers
        if self.bouncing:
            for center in self.centers:
                #Reverse the velocity if out-of-bounds
                center.velocity[(center.loc < MAX_VEL)|
                                (center.loc > DIM - MAX_VEL)] *= -1
                center.move()
        else: #Delete out-of-bound centers
            oob = {center for center in self.centers
                   if ((center.loc < 0)|(DIM < center.loc)).any()}
            self.centers.difference_update(oob)
            for center in self.centers:
                center.move()

        #Movement for color center
        keys_directions = ((pygame.K_w, (  0, -.5)),
                           (pygame.K_s, (  0,  .5)),
                           (pygame.K_a, (-.5,   0)),
                           (pygame.K_d, ( .5,   0)))

        for key, direction in keys_directions:
            if self.keys[key]:
                self.color_center.delta_velocity(direction)
        self.color_center.move()
        self.color_center.loc %= DIM

    def color(self, geometry, dual=False):
            """
            A rainbow color function exactly as the one found in lolcat.
            (see https://github.com/busyloop/lolcat)

            Color depends on distance from color center. Feel free to
            experiment with the frequency.

            One could easily use any ol' function, so long as the function's
            output is an integer between 0 and 255.
            """
            if dual:
                factor = ConvexHull(geometry).area
            else:
                factor = np.linalg.norm(self.color_center.loc - geometry)
            color = (127 * np.sin(.01 * factor + np.array((0, 2 * np.pi / 3, 4 * np.pi / 3)))
                     + 128).astype(int)
            return self.palette(color)

    def draw_voronoi_cells(self):
        """
        This function will handle drawing voronoi cells, drawing cell outlines,
        coloring cells.
        """


        points = [center.loc for center in self.centers]
        points.append(self.color_center.loc)

        try:
            vor = Voronoi(points)
        except (QhullError, ValueError):
            #Either too few points or points are degenerate.
            return
        #-----------------------------------------------------------------
        #'polygons' equals all Voronoi regions with at least 3 drawable
        #vertices (We can't draw a polygon with fewer than 3 points.) along
        #with the center associated with each region. (We use the center
        #location to color the region.)
        #
        #vor.regions is a list of lists (a list for each region) of indices
        #of points in vor.vertices; in these lists a '-1' represents a
        #"point at infinity" -- these aren't drawable so we "forget" these
        #in our polygons list.
        #-----------------------------------------------------------------
        polygons = [(vor.points[np.where(vor.point_region == i)],
                     [vor.vertices[j].astype(int) for j in reg if j != -1])
                    for i, reg in enumerate(vor.regions)
                    if len(reg) > 3 or (len(reg) == 3 and -1 not in reg)]

        if self.fill:
            for center, poly in polygons:
                polygon(self.WINDOW, self.color(center), poly)

        if self.outline:
            for _, poly in polygons:
                aalines(self.WINDOW, (255, 255, 255), True, poly, 1)

    def draw_voronoi_dual(self):
        """
        Draws the Delaunay triangulation of cell centers.
        """

        points = [center.loc for center in self.centers]
        points.append(self.color_center.loc)
        try:
            dual = Delaunay(points)
        except (QhullError, ValueError):
            #Either too few points or points are degenerate.
            return

        simplices = [[dual.points[i].astype(int) for i in simplex] for simplex in dual.simplices]

        if self.fill:
            for simplex in simplices:
                polygon(self.WINDOW, self.color(simplex, dual=True), simplex)

        if self.outline:
            for simplex in simplices:
                aalines(self.WINDOW, (255, 255, 255), True, simplex, 1)

    def draw_centers(self):
        """
        Draws a tiny circle at each center location.
        """
        for center in self.centers:
            circle(self.WINDOW, (255, 255, 255), center.loc.astype(int), 3)

        circle(self.WINDOW, (0, 0, 0), self.color_center.loc.astype(int), 5)

    def draw_help(self):
        """
        Draws a help menu.
        """
        help_background = pygame.Surface((670, 375))
        help_background.set_alpha(140)
        help_background.fill((0, 0, 0))
        help_coordinates = ((DIM - np.array([670.0, 375.0])) // 2).astype(int)
        self.WINDOW.blit(help_background, help_coordinates)
        for i, line in enumerate(self.HELP):
            self.WINDOW.blit(line, help_coordinates + (25, 16 + 25 * i))

    def get_user_input(self):
        """
        Get user input and do stuff with it.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_v:
                    self.voronoi_dual = not self.voronoi_dual
                elif event.key == pygame.K_h:
                    self.centers_visible = not self.centers_visible
                elif event.key == pygame.K_b:
                    self.bouncing = not self.bouncing
                elif event.key == pygame.K_f:
                    self.fill = not self.fill
                elif event.key == pygame.K_o:
                    self.outline = not self.outline
                elif event.key == pygame.K_ESCAPE:
                    self.show_help = not self.show_help
                elif event.key == pygame.K_UP:
                    new_index = (self.PALETTES.index(self.palette) + 1) % len(self.PALETTES)
                    self.palette = self.PALETTES[new_index]
                elif event.key == pygame.K_SPACE:
                    self.poke(self.color_center.loc)
                else:
                    self.keys[event.key] = True
            elif event.type == pygame.KEYUP:
                self.keys[event.key] = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left-Click
                    self.poke(np.array(mouse_xy()))
                elif event.button == 3:  # right-Click
                    self.centers.add(Center(np.array(mouse_xy()).astype(float)))

    def reset(self):
        """
        Reset position of the cell centers.
        """
        self.centers = {Center((np.random.random(2) * (DIM - 2 * MAX_VEL)) + MAX_VEL)
                        for _ in range(NUMBER_OF_CENTERS)}

    def poke(self, loc):
        """
        Calculates how much a poke affects every center's velocity.
        """
        for center in self.centers:
            center.delta_velocity(poke_power(loc, center.loc))
        self.color_center.delta_velocity(poke_power(loc, self.color_center.loc))

    def start(self):
        pygame.init()
        pygame.display.set_caption('Soap')
        self.render_help()
        while self.running:
            self.WINDOW.fill((63, 63, 63))
            if self.outline or self.fill:
                if self.voronoi_dual:
                    self.draw_voronoi_dual()
                else:
                    self.draw_voronoi_cells()
            if self.centers_visible:
                self.draw_centers()
            if self.show_help:
                self.draw_help()
            pygame.display.update()
            self.get_user_input()
            self.move_centers()
        pygame.quit()

if __name__ == "__main__":
    Soap().start()
