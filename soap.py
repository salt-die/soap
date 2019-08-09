#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
soap: a useless experiment in pygame

Poke dynamic voronoi cells by left-clicking or create new cells by right-
clicking.
"""
from numpy import pi, array, where, sin
from numpy.linalg import norm
from numpy.random import random_sample
from scipy.spatial.qhull import QhullError, Voronoi, Delaunay, ConvexHull
import pygame
import pygame.freetype #For loading font
from pygame.mouse import get_pos as mouse_xy
from pygame.draw import polygon, aalines, circle

class Center:
    """
    Cell center class.  Cell centers have methods that affect their movement.
    """
    def __init__(self, loc, velocity, max_vel):
        self.loc = loc
        self.velocity = velocity
        self.max_vel = max_vel

    def friction(self):
        """
        Applies friction and limits the magnitude of velocity.

        The friction constant, fric, should satisfy 0 < fric < 1.
        Don't fric it up.
        """
        fric = .97
        self.velocity *= fric
        self.velocity[abs(self.velocity) < .01] = 0.0   #Prevent jitter.
        magnitude = norm(self.velocity)
        if magnitude > self.max_vel:
            self.velocity *= self.max_vel / magnitude

    def delta_velocity(self, delta):
        """
        This adds delta to the velocity and then limits the velocity to
        max_vel.
        """
        self.velocity += delta
        magnitude = norm(self.velocity)
        if magnitude > self.max_vel:
            self.velocity *= self.max_vel / magnitude

    def move(self):
        """
        Apply velocity to location.
        """
        self.loc += self.velocity

def game():
    """
    The main game functions, constants, and variables, along with the main
    while loop.
    """
    def render_help():
        """
        Turns help_text into a surface that pygame can blit.
        """
        nonlocal help_text
        font = pygame.freetype.Font('NotoSansMono-Regular.ttf', 20)
        help_text = [font.render(text, (255, 255, 255)) for text in help_text]
        help_text = [i for i, _ in help_text] #Throw away the rect-like tuples

    #Game Functions-----------------------------------------------------------
    def move_centers():
        """
        Handle behavior of cell center movement at the boundaries. Then
        apply friction and move each cell center.

        Also handles the manual movement of color center.
        """
        #Movement for cell centers
        if booleans_dict["bouncing"]:
            for center in centers:
                #Reverse the velocity if out-of-bounds
                center.velocity[(center.loc < max_vel)|\
                                (center.loc > window_dim - max_vel)] *= -1
                center.friction()
                center.move()
        else: #Delete out-of-bound centers
            oob = {center for center in centers\
                   if ((center.loc < 0)|(window_dim < center.loc)).any()}
            centers.difference_update(oob)
            for center in centers:
                center.friction()
                center.move()

        #Movement for color center
        if not (booleans_dict["up"] or\
                booleans_dict["down"] or\
                booleans_dict["left"] or\
                booleans_dict["right"]):
            color_center.friction()
            color_center.move()
        else:
            if booleans_dict["up"]:
                color_center.delta_velocity(array((0, -.5)))
            if booleans_dict["down"]:
                color_center.delta_velocity(array((0, .5)))
            if booleans_dict["left"]:
                color_center.delta_velocity(array((-.5, 0)))
            if booleans_dict["right"]:
                color_center.delta_velocity(array((.5, 0)))
            color_center.move()
        #"Wrap" around the screen instead of heading out-of-bounds
        color_center.loc %= window_dim

    def draw_voronoi_cells():
        """
        This function will handle drawing voronoi cells, drawing cell outlines,
        coloring cells.
        """
        def get_color(point):
            """
            A rainbow color function exactly as the one found in lolcat.
            (see https://github.com/busyloop/lolcat)

            Color depends on distance from color center. Feel free to
            experiment with the frequency.

            One could easily use any ol' function, so long as the function's
            output is an integer between 0 and 255.
            """
            frequency = .01
            distance = norm(color_center.loc - point)
            color = (127 * sin(frequency * distance +\
                               array((0, 2*pi/3, 4*pi/3))) + 128).astype(int)
            return palette(color)

        points = [center.loc for center in centers]
        points.append(color_center.loc)

        try:
            vor = Voronoi(points)
        except (QhullError, ValueError):
            #Either too few points or points are degenerate.
            #Everything is fine, we just won't draw any cells.
            #Leave the function quietly!
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
        polygons = [(vor.points[where(vor.point_region == i)],\
                    [vor.vertices[j] for j in reg if j != -1])\
                    for i, reg in enumerate(vor.regions)\
                    if len(reg) > 3 or (len(reg) == 3 and -1 not in reg)]

        if booleans_dict["fill"]:
            for center, poly in polygons:
                polygon(window, get_color(center), poly)

        if booleans_dict["outline"]:
            for _, poly in polygons:
                aalines(window, (255, 255, 255), True, poly, 1)

    def draw_voronoi_dual():
        """
        Draws the Delaunay triangulation of cell centers.
        """
        def get_color(simplex):
            """
            A rainbow color function exactly as the one found in lolcat.
            (see https://github.com/busyloop/lolcat)

            Color depends on area of simplex.
            """
            frequency = .01
            area = ConvexHull(simplex).area
            color = (127 * sin(frequency * area +\
                               array((0, 2*pi/3, 4*pi/3))) + 128).astype(int)
            return palette(color)
        points = [center.loc for center in centers]
        points.append(color_center.loc)
        try:
            dual = Delaunay(points)
        except (QhullError, ValueError):
            #Either too few points or points are degenerate.
            #Everything is fine, we just won't draw any simplices.
            #Leave the function quietly!
            return

        simplices = [[dual.points[i] for i in simplex]\
                     for simplex in dual.simplices]

        if booleans_dict["fill"]:
            for simplex in simplices:
                polygon(window, get_color(simplex), simplex)

        if booleans_dict["outline"]:
            for simplex in simplices:
                aalines(window, (255, 255, 255), True, simplex, 1)

    def draw_centers():
        """
        Draws a tiny circle at each center location.
        """
        for center in centers:
            circle(window, (255, 255, 255), center.loc.astype(int), 3)

        circle(window, (0, 0, 0), color_center.loc.astype(int), 5)

    def draw_help():
        """
        Draws a help menu.
        """
        help_background = pygame.Surface((670, 375))
        help_background.set_alpha(140)
        help_background.fill((0, 0, 0))
        help_coordinates = (window_dim - array([670.0, 375.0])) // 2
        window.blit(help_background, help_coordinates)
        for i, line in enumerate(help_text):
            window.blit(line, help_coordinates+array([25, 16 + 25 * i]))

    #INPUT FUNCTIONS----------------------------------------------------------
    def get_user_input():
        """
        Get user input and do stuff with it.
        """
        wasd = {97, 115, 100, 119}
        for event in pygame.event.get():
            if event.type == 12: #Quit
                booleans_dict["running"] = False
            elif event.type == 2: #key down
                keydown_dict.get(event.key, no_key)()
                if event.key in wasd:
                    color_move_start(event.key)
                elif event.key == 32: #space
                    poke(color_center.loc)
            elif event.type == 3: #key up
                if event.key in wasd:
                    color_move_stop(event.key)
            elif event.type == 5: #Mouse down
                if event.button == 1:   #left-Click
                    poke(array(mouse_xy()))
                elif event.button == 3: #right-Click
                    centers.add(Center(array(mouse_xy()).astype(float),\
                                       array([0.0, 0.0]), max_vel))

    def reset():
        """
        Reset position of the cell centers.
        """
        nonlocal centers
        centers = {Center((random_sample(2) * (window_dim - 2 * max_vel))\
                          + max_vel,\
                          array([0.0, 0.0]),\
                          max_vel)\
                   for i in range(number_of_centers)}

    def toggle_dual():
        """
        Toggle showing Voronoi dual.
        """
        booleans_dict["voronoi_dual"] = not booleans_dict["voronoi_dual"]

    def toggle_centers():
        """
        Toggle showing cell centers.
        """
        booleans_dict["centers_visible"] = not booleans_dict["centers_visible"]

    def toggle_bouncing():
        """
        Toggle bouncing off boundaries. If off, out-of-bound centers are
        deleted.
        """
        booleans_dict["bouncing"] = not booleans_dict["bouncing"]

    def toggle_fill():
        """
        Toggle coloring the Voronoi cells.
        """
        booleans_dict["fill"] = not booleans_dict["fill"]

    def toggle_outline():
        """
        Toggle drawing the outling of the Voronoi cells.
        """
        booleans_dict["outline"] = not booleans_dict["outline"]

    def next_palette():
        """
        Change the colors used to fill Voronoi cells.
        """
        nonlocal palette
        palette = palettes[(palettes.index(palette) + 1) % len(palettes)]

    def toggle_help():
        """
        Show the help menu.
        """
        booleans_dict["show_help"] = not booleans_dict["show_help"]

    def no_key():
        """
        Empty function.
        """
        pass

    def color_move_start(key):
        """
        Start moving the color center in the corresponding direction.
        """
        if key == 119:
            booleans_dict["up"] = True
        elif key == 97:
            booleans_dict["left"] = True
        elif key == 115:
            booleans_dict["down"] = True
        elif key == 100:
            booleans_dict["right"] = True

    def color_move_stop(key):
        """
        Stop moving the color center in the corresponding direction.
        """
        if key == 119:
            booleans_dict["up"] = False
        elif key == 97:
            booleans_dict["left"] = False
        elif key == 115:
            booleans_dict["down"] = False
        elif key == 100:
            booleans_dict["right"] = False

    def poke(loc):
        """
        Calculates how much a poke affects every center's velocity.
        Feel free to play with the constants below.
        """
        def poke_power(poke_loc, center_loc):
            """
            Returns the force vector of a poke.
            """
            difference = center_loc - poke_loc
            distance = norm(difference)
            #Leading constant can be modified -- if,else prevents divide by 0
            return 100000 * difference/distance**3 if distance != 0 else 0

        for center in centers:
            center.delta_velocity(poke_power(loc, center.loc))
        color_center.delta_velocity(poke_power(loc, color_center.loc))

    #Game variables-----------------------------------------------------------

    #Window dimensions should be at least 670 x 375 to not clip help_menu.
    window_dim = array([800.0, 800.0])
    window = pygame.display.set_mode(window_dim.astype(int))

    help_text = ["left-click to poke the centers",\
                 "right-click to create a new center",\
                 "w,a,s,d moves the color center",\
                 "space creates a poke at the color center's location",\
                 "----------------------------------",\
                 "Options:",\
                 "esc -- Toggles this menu",\
                 "r   -- Reset centers",\
                 "v   -- Toggle Voronoi dual",\
                 "b   -- Toggle bouncing (delete out-of-bound centers)",\
                 "f   -- Toggle fill of Voronoi cells",\
                 "o   -- Toggle outline of Voronoi cells",\
                 "h   -- Toggle showing centers of Voronoi cells",\
                 "up  -- Cycle through color palettes"]
    render_help()

    #If adding to palettes, remember input: output will be 3-tuples with each
    #element an integer between 0 and 255.
    palettes = [lambda color: color,\
                lambda color: (color[0], color[0], 255),\
                lambda color: (color[0], color[1], 155),\
                lambda color: (color[0], color[1], color[1]),\
                lambda color: (color[0], color[0], color[0]),\
                lambda color: (color[0], color[0], color[2]),\
                lambda color: (155, 100, color[0])]
    palette = palettes[0]

    #For get_user_input()
    keydown_dict = {114: reset,          #'r'
                    118: toggle_dual,    #'v'
                    104: toggle_centers, #'h'
                    98: toggle_bouncing, #'b'
                    102: toggle_fill,    #'f'
                    111: toggle_outline, #'o'
                    273: next_palette,   #'up'
                    27: toggle_help,}    #'esc'

    clock = pygame.time.Clock() #For limiting fps

    max_vel = 15.0 #Max Velocity of cell centers

    #Convenient storage of all booleans
    booleans_dict = {"voronoi_dual" : False,
                     "bouncing" : True,
                     "fill": True,
                     "outline" : True,
                     "show_help" : True,
                     "running" : True,
                     "centers_visible" : False,
                     "up" : False,
                     "down" : False,
                     "left" : False,
                     "right" : False}

    number_of_centers = 50 #Initial number of cell centers
    centers = {}
    reset() #Randomly place cell centers
    #-----------------------------------------------------------------------
    #The color center is controlled with w,a,s,d. The distance from the color
    #center to the centers of voronoi cells determines those cells colors.
    #-----------------------------------------------------------------------
    color_center = Center(window_dim/2, array([0.0, 0.0]), max_vel)

    #Main Loop----------------------------------------------------------------
    while booleans_dict["running"]:
        window.fill((63, 63, 63))
        if booleans_dict["outline"] or booleans_dict["fill"]:
            if booleans_dict["voronoi_dual"]:
                draw_voronoi_dual()
            else:
                draw_voronoi_cells()
        if booleans_dict["centers_visible"]:
            draw_centers()
        if booleans_dict["show_help"]:
            draw_help()
        clock.tick(40)  #Limit frames per second (Comment out if you'd like)
        pygame.display.update()
        get_user_input()
        move_centers()

def main():
    """
    Starts the game.
    """
    pygame.init()
    pygame.display.set_caption('Soap')
    game()
    pygame.quit()

if __name__ == "__main__":
    main()
