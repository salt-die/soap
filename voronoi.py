#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pygame
import pygame.freetype #For loading font
from pygame.draw import polygon, aalines, circle
from pygame.locals import QUIT, KEYDOWN, KEYUP, MOUSEBUTTONDOWN
from numpy import pi, array, where, sin
from numpy.linalg import norm
from random import randint
from scipy.spatial import Voronoi

class Center:
    def __init__(self, loc, velocity):
        self.loc = loc
        self.velocity = velocity

def game():
    """
    The main game functions, constants, and variables, along with the main
    while loop.
    """
    #Game Functions-----------------------------------------------------------
    def move_centers():
        """
        Decelerate each cell center and then move each cell center according to
        its new velocity.

        Also handles manual movement of color center.
        """
        def friction(current_velocity):
            """
            The friction constant, fric, should satisfy 0 < fric < 1.
            Don't fric it up.
            """
            fric = .97
            current_velocity = fric * current_velocity
            current_velocity[abs(current_velocity) < .01] = 0.0 #Prevent jitter
            current_velocity[current_velocity > 15] = 15.0      #and prevent
            current_velocity[current_velocity < -15] = -15.0    #out-of-bounds
            return current_velocity

        def decel_and_move(center):
            center.velocity = friction(center.velocity)
            center.loc += center.velocity

        if BOUNCING:
            for center in centers:
                #Reverse the velocity if out-of-bounds
                center.velocity[(center.loc < 15) | (center.loc > 985)] *= -1
                decel_and_move(center)
        else: #Delete out-of-bound centers
            oob = [center\
                   for center in centers\
                   for coor in center.loc\
                   if not 0 < coor < 1000]
            for center in oob: centers.remove(center)
            for center in centers: decel_and_move(center)

        #Movement for color center
        if not (UP or DOWN or LEFT or RIGHT):
            decel_and_move(color_center)
        else:
            if UP and color_center.velocity[1] > -15:
                color_center.velocity[1] -= .5
            if DOWN and color_center.velocity[1] < 15:
                color_center.velocity[1] += .5
            if LEFT and color_center.velocity[0] > -15:
                color_center.velocity[0] -= .5
            if RIGHT and color_center.velocity[1] < 15:
                color_center.velocity[0] += .5
            color_center.loc += color_center.velocity
        #"Wrap" around the screen instead of heading out-of-bounds
        color_center.loc %= 1000

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
            color = [int(sin(frequency * distance + offset) * 127 + 128)\
                     for offset in [0, 2*pi/3, 4*pi/3]]
            return PALETTE(color)

        POINTS = [center.loc for center in centers]
        try:
            vor = Voronoi(POINTS)
        except:
            #Either too few POINTS or POINTs are colinear.
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
                    for i,reg in enumerate(vor.regions)\
                    if len(reg)>3 or (len(reg)==3 and -1 not in reg)]

        if FILL:
            for center,poly in polygons:
                polygon(WINDOW, get_color(center), poly)

        if OUTLINE:
            for _,poly in polygons:
                aalines(WINDOW, (255, 255, 255), True, poly, 1)

    def draw_centers():
        """
        Draws a tiny circle at each center location.
        """
        for center in centers:
                circle(WINDOW, (255, 255, 255), center.loc.astype(int), 3)
        circle(WINDOW, (0, 0, 0), color_center.loc.astype(int), 5)

    def draw_help():
        """
        Draws a help menu.
        """
        bg = pygame.Surface((670,325))
        bg.set_alpha(140)
        bg.fill((0, 0, 0))
        WINDOW.blit(bg, (165,337))
        for i, surface in enumerate(help_text):
                WINDOW.blit(surface, (191, 353 + 25 * i))

    #INPUT FUNCTIONS----------------------------------------------------------
    def user_input():
        for event in pygame.event.get():
            if event.type == QUIT:
                nonlocal running
                running = False
            elif event.type == KEYDOWN:
                KEYDOWN_dict.get(event.key, no_key)()
                if event.key in {97, 115, 100, 119}:
                    color_move_start(event.key)
            elif event.type == KEYUP:
                if event.key in {97, 115, 100, 119}:
                    color_move_stop(event.key)
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:   #Left-Click
                    mouseX, mouseY = pygame.mouse.get_pos()
                    poke(array([mouseX, mouseY]))
                elif event.button == 3: #Right-Click
                    mouseX, mouseY = pygame.mouse.get_pos()
                    centers.append(Center(array([mouseX,\
                                                 mouseY]).astype(float),\
                                   array([0.0, 0.0])))

    def reset():
        nonlocal centers
        centers = [Center(array([randint(0,999),\
                                 randint(0,999)]).astype(float),\
                          array([0.0, 0.0]))\
                   for i in range(number_of_centers)]

    def toggle_centers():
        nonlocal CENTERS_VISIBLE
        CENTERS_VISIBLE = not CENTERS_VISIBLE

    def toggle_bouncing():
        nonlocal BOUNCING
        BOUNCING = not BOUNCING

    def toggle_fill():
        nonlocal FILL
        FILL = not FILL

    def toggle_outline():
        nonlocal OUTLINE
        OUTLINE = not OUTLINE

    def next_palette():
        nonlocal PALETTE
        PALETTE = palettes[(palettes.index(PALETTE) + 1 ) % len(palettes)]

    def toggle_help():
        nonlocal HELP
        HELP = not HELP

    def no_key():
        pass

    def color_move_start(key):
        if key == 119:
            nonlocal UP
            UP = True
        elif key == 97:
            nonlocal LEFT
            LEFT = True
        elif key == 115:
            nonlocal DOWN
            DOWN = True
        elif key == 100:
            nonlocal RIGHT
            RIGHT = True

    def color_move_stop(key):
        if key == 119:
            nonlocal UP
            UP = False
        elif key == 97:
            nonlocal LEFT
            LEFT = False
        elif key == 115:
            nonlocal DOWN
            DOWN = False
        elif key == 100:
            nonlocal RIGHT
            RIGHT = False

    def poke(loc):
        """
        Calculates how much a poke affects every center's velocity.
        Feel free to play with the constants below.
        """
        for center in centers:
            #Differences of coordinates of poke and center
            difference = center.loc - loc
            #Distance between poke and center
            distance = norm(difference)
            if distance == 0: #Prevent divide by zero
                distance = .001
            #Magnitude of poke
            poke_mag = 100000 / distance**2
            if poke_mag > 200: #Limit magnitude of poke
                poke_mag = 200
            #Update velocity according to magnitude and direction
            center.velocity += poke_mag * difference/distance

    #Game constants-----------------------------------------------------------
    BACKGROUND_COLOR  = (63, 63, 63)
    WINDOW = pygame.display.set_mode((1000, 1000))
    help_text = ["Left-click to poke the centers.",\
                 "Right-click to create a new center.",\
                 "w,a,s,d moves the color center.",\
                 "----------------------------------",\
                 "Options:",\
                 "esc -- Toggles this menu",\
                 "r   -- Reset centers",\
                 "b   -- Toggle bouncing (delete out-of-bound centers)",\
                 "f   -- Toggle fill of Voronoi cells",\
                 "o   -- Toggle outline of Voronoi cells",\
                 "h   -- Toggle showing centers of Voronoi cells",\
                 "up  -- Cycle through color palettes"]
    myfont = pygame.freetype.Font('NotoSansMono-Regular.ttf', 20)
    help_text = [myfont.render(text, (255, 255, 255)) for text in help_text]
    help_text = [i for i,_ in help_text] #Throw away the rect-like tuples
    #Experimenting with palettes is fun! Remember that color will be a 3-tuple
    #(R, G, B) if adding your own function here.
    palettes = [lambda color: color,\
                lambda color: (color[0], color[0], 255),\
                lambda color: (color[0], color[1], 155),\
                lambda color: (color[0], color[1], color[1]),\
                lambda color: (color[0], color[0], color[0]),\
                lambda color: (color[0], color[0], color[2]),\
                lambda color: (155, 100, color[0])]
    number_of_centers = 50
    KEYDOWN_dict = {114: reset,          #'r'
                    104: toggle_centers, #'h'
                    98: toggle_bouncing, #'b'
                    102: toggle_fill,    #'f'
                    111: toggle_outline, #'o'
                    273: next_palette,   #'up'
                    27: toggle_help,}    #'esc'
    clock = pygame.time.Clock()

    #Game Variables-----------------------------------------------------------
    centers = []; reset() #Create and randomly place cell centers
    #-----------------------------------------------------------------------
    #The color center is controlled with w,a,s,d. The distance from the color
    #center to the centers of voronoi cells determines those cells colors.
    #-----------------------------------------------------------------------
    color_center = Center(array([500.0,500.0]), array([0.0, 0.0]))
    PALETTE = palettes[0]
    BOUNCING = FILL = OUTLINE = HELP = running = True
    CENTERS_VISIBLE = UP = DOWN = LEFT = RIGHT = False

    #Main Loop----------------------------------------------------------------
    while running:
        WINDOW.fill(BACKGROUND_COLOR)
        if OUTLINE or FILL: draw_voronoi_cells()
        if CENTERS_VISIBLE: draw_centers()
        if HELP: draw_help()
        clock.tick(40)  #Limit frames per second (Comment out if you'd like)
        pygame.display.update()
        user_input()
        move_centers()
    pygame.quit()

def main():
    pygame.init()
    pygame.display.set_caption('Soap')
    game()

if __name__ == "__main__":
    main()