import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def     __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, OUR_FIELD, PROTECTED_FIELD, STRUCT_FIELD
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]

        PROTECTED_FIELD = [1000] * 28
        for i in range(28):
            PROTECTED_FIELD[i] = [1000] * 28
        for i in range(0, 14):
            j = 0
            while j <= i:
                PROTECTED_FIELD[13 - j][i] = 0
                PROTECTED_FIELD[14 + j][i] = 0
                j += 1
        OUR_FIELD = []
        for i in range(14):
            j = 0
            while j <= i:
                OUR_FIELD.append([13 - j, i])
                OUR_FIELD.append([14 + j, i])
                j += 1


        STRUCT_FIELD = [-100] * 28
        for i in range(28):
            STRUCT_FIELD[i] = [-100] * 28
        for i in range(0, 14):
            j = 0
            while j <= i:
                STRUCT_FIELD[13 - j][i] = 0
                STRUCT_FIELD[14 + j][i] = 0
                j += 1

        MP = 0
        SP = 0
        # This is a good place to do initial setup

        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """in_arena_bounds
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def mark_def_point(self, game_state, turrets_placed):
        for turret in turrets_placed:
            self.mark_around_turrel(game_state, turret)

    def mark_around_turrel(self, game_state, location):
        if not gamelib.game_map.GameMap.in_arena_bounds(game_state.game_map, location):
            return False
        location_in_range = game_state.game_map.get_locations_in_range(location, 3.5)
        for loco in location_in_range:
            PROTECTED_FIELD[loco[0]][loco[1]] += 1
        return True

    def build_neeeded_walls(self, game_state, walls_placed, turrets_placed):
        if len(walls_placed) >= len(turrets_placed):
            return True
        missed_walls = []
        for turret in turrets_placed:
            try:
                walls_placed.index([turret[0], turret[1]+1])
            except ValueError:
                missed_walls.append([turret[0], turret[1]+1])
        #TODO Make priority of making walls by hp of turret
        self.spawn_and_mark(game_state, missed_walls, WALL)
        self.upgrade_and_mark(game_state, missed_walls, WALL)


    def get_less_defended_rating(self):
        minimal_vage = 100
        curr_y = 11
        for i in range(28):
            if minimal_vage > PROTECTED_FIELD[i][curr_y]:
                minimal_vage = PROTECTED_FIELD[i][curr_y]
        return minimal_vage

    def get_most_defended_x(self, curr_y):
        maximal_vage = -1
        for i in range(28):
            if maximal_vage < PROTECTED_FIELD[i][curr_y] < 500:
                maximal_vage = PROTECTED_FIELD[i][curr_y]
        return maximal_vage

    def choose_best_tower_loco(self, game_state, ):
        minimal_vage = self.get_less_defended_rating()
        curr_y = 11
        best_loco = self.get_all_locations_line_by_rate(curr_y, minimal_vage)
        #TODO Remove try block, bug cause of wrong ARR_FIELD some param
        try:
            best_one = self.choose_best_var(game_state, best_loco)
            while not gamelib.game_map.GameMap.in_arena_bounds(game_state.game_map, best_one):
                best_loco.remove(best_one)
                best_one = self.choose_best_var(game_state, best_loco)
        except IndexError:
            best_one = [-1, -1]
        return best_one

    def choose_best_var(self, game_state, best_loco):
        sum_of_points = []
        for location in best_loco:
            location_in_range = game_state.game_map.get_locations_in_range(location, 3.5)
            sum_of_loco = 0
            count_of_parts = 0
            for loco in location_in_range:
                sum_of_loco += PROTECTED_FIELD[loco[0]][loco[1]]
                count_of_parts += 1
            if count_of_parts == 0:
                sum_of_points.append(1000)
            else:
                sum_of_points.append(sum_of_loco / count_of_parts)
        min_sum = 1000
        index = 0
        for sum in sum_of_points:
            if min_sum > sum:
                index = sum_of_points.index(sum)
                min_sum = sum
        return best_loco[index]
    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def choose_place_of_support(self, game_state):
        curr_y = 10
        most_profitable_place = [13, 10]
        maximal_rate = self.get_most_defended_x(curr_y)
        best_loco = self.get_all_locations_line_by_rate(curr_y, maximal_rate)
        #TODO Summury score = coverage ration * price current structures
        if len(best_loco) == 1:
            return best_loco[0]

        max_score = -1
        answer = best_loco[0]
        for location in best_loco:
            ration = len(game_state.game_map.get_locations_in_range(location, 7)) / len(game_state.game_map.get_locations_in_range(most_profitable_place, 7))
            price_struct = self.get_sum_of_walls_and_turrets_in_range(game_state, location, 7)
            score = ration * price_struct
            if max_score < score:
                answer = location
        return answer


    def get_sum_of_walls_and_turrets_in_range(self, game_state, start_pos, range):
        summa = 0
        all_locations = game_state.game_map.get_locations_in_range(start_pos, range)
        for location in all_locations:
            if STRUCT_FIELD[location[0]][location[1]] != 0 and STRUCT_FIELD[location[0]][location[1]] != 4 and STRUCT_FIELD[location[0]][location[1]] != 8:
                summa += STRUCT_FIELD[location[0]][location[1]]
        return summa

    def get_all_locations_line_by_rate(self, curr_y, rate):
        best_loco = []
        for i in range(28):
            if rate == PROTECTED_FIELD[i][curr_y]:
                best_loco.append([i, rate])
        return best_loco

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        if game_state.turn_number < 1:
            self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored

        placed_units = self.get_blocked_locations(OUR_FIELD, game_state)
        turrels_placed = []
        supports_placed = []
        walls_placed = []
        for location in placed_units:
            unit = game_state.contains_stationary_unit(location)
            string_unit = str(unit)
            if string_unit.find("Friendly DF") != -1:
                turrels_placed.append(location)
            else:
                if string_unit.find("Friendly EF") != -1:
                    supports_placed.append(location)
                else:
                    walls_placed.append(location)
        self.mark_def_point(game_state, turrels_placed)
        self.map_units(game_state, walls_placed, WALL)
        self.map_units(game_state, turrels_placed, TURRET)
        self.map_units(game_state, supports_placed, SUPPORT)
        if self.get_less_defended_rating() != 0:
            self.build_neeeded_walls(game_state, walls_placed, turrels_placed)
        else:
            game_state.attempt_spawn(INTERCEPTOR, [22, 8], 2)
            game_state.attempt_spawn(INTERCEPTOR, [5, 8], 2)
        # If the turn is less than 5, stall with interceptors and wait to see enemy's base

        while game_state.get_resource(SP) >= 10:
            sp_in_start_round = game_state.get_resource(SP)
            best_loco = self.choose_best_tower_loco(game_state)
            if best_loco[0] == -1:
                break
            self.spawn_and_mark(game_state, best_loco, TURRET)
            self.upgrade_and_mark(game_state, best_loco, TURRET)
            self.place_walls_close_to_turrles(game_state, best_loco)
            if sp_in_start_round == game_state.get_resource(SP):
                break

        if game_state.get_resource(SP) >= 13:
            support_loco = self.choose_place_of_support(game_state)
            self.spawn_and_mark(game_state, support_loco, SUPPORT)
            self.upgrade_and_mark(game_state, support_loco, SUPPORT)
            wall_loco = [[[support_loco[0] + 1], [support_loco[1]]], [[support_loco[0] - 1], [support_loco[1]]]]
            self.spawn_and_mark(game_state, wall_loco, WALL)
            self.upgrade_and_mark(game_state, wall_loco, WALL)

        if game_state.get_resource(MP) >= 9:
            self.demolisher_line_strategy(game_state)


    def place_walls_close_to_turrles(self, game_state, turret):
        turret[1] += 1
        turret[0] += 1
        self.spawn_and_mark(game_state, turret, WALL)
        self.upgrade_and_mark(game_state, turret, WALL)
        turret[0] -= 2
        self.spawn_and_mark(game_state, turret, WALL)
        self.upgrade_and_mark(game_state, turret, WALL)

    def is_unit_upgrade(self, game_state, location):
        for unit in game_state.game_map[location[0], location[1]]:
            if unit.stationary:
                existing_unit = unit
        return existing_unit.upgraded

    def make_false_array_real(self, array):
        gamelib.util.debug_write("In make false real")
        gamelib.util.debug_write(array)
        real_array = []
        try:
            for unit in array:
                gamelib.util.debug_write(str(unit[0]))
                break
            real_array = array
        except TypeError:
            real_array.append(array)
        return real_array

    def map_units(self, game_state, unit_array, unit_type):
        real_array = self.make_false_array_real(unit_array)
        regular_cost = 0
        upgrade_cost = 0
        if unit_type == WALL:
            regular_cost = 1
            upgrade_cost = 3
        else:
            if unit_type == TURRET:
                regular_cost = 2
                upgrade_cost = 6
            else:
                regular_cost = 4
                upgrade_cost = 8
        for unit in real_array:
            if self.is_unit_upgrade(game_state, unit):
                STRUCT_FIELD[unit[0]][unit[1]] = upgrade_cost
            else:
                STRUCT_FIELD[unit[0]][unit[1]] = regular_cost

    def spawn_and_mark(self, game_state, unit_array, unit_type):
        gamelib.util.debug_write("In spawn and mark")
        real_array = self.make_false_array_real(unit_array)
        gamelib.util.debug_write(real_array)
        for unit in real_array:
            if game_state.attempt_spawn(unit_type, unit) > 1:
                self.map_units(game_state, unit, unit_type)

    def upgrade_and_mark(self, game_state, unit_array, unit_type):
        gamelib.util.debug_write("In upgrade and mark")
        real_array = self.make_false_array_real(unit_array)
        gamelib.util.debug_write(real_array)
        for unit in real_array:
            if game_state.attempt_upgrade(unit) > 0:
                self.map_units(game_state, unit, unit_type)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[3, 11], [13, 11], [24, 11]]
        wall_updates = [[13, 12], [3, 12]]
        wall_locations = [[0, 13], [1, 13], [26, 13], [27, 13], [24, 12]]
        #support_locations = []

        self.spawn_and_mark(game_state, turret_locations, TURRET)
        self.spawn_and_mark(game_state, wall_locations, WALL)
        self.spawn_and_mark(game_state, wall_updates, WALL)
        self.upgrade_and_mark(game_state, wall_updates, WALL)
        self.upgrade_and_mark(game_state, turret_locations, TURRET)


    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [20, 6], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_blocked_locations(selfs, locations, game_state):
        filtered = []
        for location in locations:
            if game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered


    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
