import gamelib
import random
import math
import warnings
from sys import maxsize
import json




class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)

    """
         ____      _      __  __   _____      ____    ___    ____    _____ 
        / ___|    / \    |  \/  | | ____|    / ___|  / _ \  |  _ \  | ____|
       | |  _    / _ \   | |\/| | |  _|     | |     | | | | | | | | |  _|  
       | |_| |  / ___ \  | |  | | | |___    | |___  | |_| | | |_| | | |___ 
        \____| /_/   \_\ |_|  |_| |_____|    \____|  \___/  |____/  |_____|
    """

    def on_game_start(self, config):
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, OUR_FIELD, PROTECTED_FIELD, STRUCT_FIELD
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]

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
                if j == 0:
                    STRUCT_FIELD[13 - j][i] = 1
                    STRUCT_FIELD[14 + j][i] = 1
                else:
                    STRUCT_FIELD[13 - j][i] = 0
                    STRUCT_FIELD[14 + j][i] = 0
                j += 1

        PROTECTED_FIELD = [1000] * 28
        for i in range(28):
            PROTECTED_FIELD[i] = [1000] * 28
        for i in range(0, 14):
            j = 0
            while j <= i:
                PROTECTED_FIELD[13 - j][i] = 0
                PROTECTED_FIELD[14 + j][i] = 0
                j += 1

        self.refresh_matrixes()
        MP = 0
        SP = 0
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)
        self.refresh_matrixes()
        self.starter_strategy(game_state)

        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """

    def starter_strategy(self, game_state):
        if self.fox_defense(game_state):
            return
        gamelib.util.debug_write(str(game_state.turn_number))

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
        #TODO remove or change function of building needed wals
        curr_y = 10
        self.defend_edges(game_state)
        self.build_neeeded_walls(game_state, curr_y)
        if self.get_less_defended_rating(curr_y) <= 1:
            game_state.attempt_spawn(INTERCEPTOR, [22, 8], 1)
            game_state.attempt_spawn(INTERCEPTOR, [5, 8], 1)

        if game_state.get_resource(MP) >= 9:
            game_state.attempt_spawn(DEMOLISHER, [20, 6], 100)
        if len(turrels_placed) != 0:
            struct_coeff = len(supports_placed) / len(turrels_placed)
        else:
            struct_coeff = 1
        if (self.get_less_defended_rating(curr_y) < 3 or struct_coeff >= 0.5) or (len(turrels_placed) > 18 and struct_coeff >= 0.75):
            best_loco = self.choose_best_tower_loco(game_state, curr_y)
            if game_state.get_resource(SP) >= 10 and best_loco[0] != -1:
                self.spawn_and_mark(game_state, best_loco, TURRET)
                self.upgrade_and_mark(game_state, best_loco, TURRET)
                self.place_wall_close_to_turrles(game_state, best_loco)
        else:
            if game_state.get_resource(SP) >= 8:
                support_loco = self.choose_place_of_support(game_state, curr_y - 1)
                gamelib.util.debug_write("      Answer is :")
                gamelib.util.debug_write(str(support_loco))
                self.spawn_and_mark(game_state, support_loco, SUPPORT)
                self.upgrade_and_mark(game_state, support_loco, SUPPORT)

        if game_state.get_resource(SP) >= 30:
            self.build_the_pass(game_state)

    """
         _   _   _____   ___   _       _____          ____    ___    ____    _____ 
        | | | | |_   _| |_ _| | |     | ____|        / ___|  / _ \  |  _ \  | ____|
        | | | |   | |    | |  | |     |  _|         | |     | | | | | | | | |  _|  
        | |_| |   | |    | |  | |___  | |___        | |___  | |_| | | |_| | | |___ 
         \___/    |_|   |___| |_____| |_____|        \____|  \___/  |____/  |_____|
                                                                                                                                                       
    """
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_health_of_structure(self, game_state, location):
        if not game_state.contains_stationary_unit(location):
            return -1
        for unit in game_state.game_map[location[0], location[1]]:
            if unit.stationary:
                existing_unit = unit
        return existing_unit.health

    def is_unit_placed(self, game_state, location):
        hp = self.get_health_of_structure(game_state, location)
        if hp == -1:
            return False
        else:
            return True

    def make_false_array_real(self, array):
        real_array = []
        try:
            for unit in array:
                unit[0] + 1
                break
            real_array = array
        except TypeError:
            real_array.append(array)
        return real_array

    def sum_of_health_unit_array(self, game_state, unit_array):
        hp = 0
        for wall in unit_array:
            hp += self.get_health_of_structure(game_state, wall)
        return hp

    def is_unit_upgrade(self, game_state, location):
        for unit in game_state.game_map[location[0], location[1]]:
            if unit.stationary:
                existing_unit = unit
        return existing_unit.upgraded

    """
         __  __  __   __         _      _        ____    ___         ____    ___    ____    _____ 
        |  \/  | \ \ / /        / \    | |      / ___|  / _ \       / ___|  / _ \  |  _ \  | ____|
        | |\/| |  \ V /        / _ \   | |     | |  _  | | | |     | |     | | | | | | | | |  _|  
        | |  | |   | |        / ___ \  | |___  | |_| | | |_| |     | |___  | |_| | | |_| | | |___ 
        |_|  |_|   |_|       /_/   \_\ |_____|  \____|  \___/       \____|  \___/  |____/  |_____|                                                                                   
    """

    def refresh_matrixes(self):
        self.STRUCT_FIELD = [-100] * 28
        for i in range(28):
            STRUCT_FIELD[i] = [-100] * 28
        for i in range(0, 14):
            j = 0
            while j <= i:
                if j == 0:
                    STRUCT_FIELD[13 - j][i] = 1
                    STRUCT_FIELD[14 + j][i] = 1
                else:
                    STRUCT_FIELD[13 - j][i] = 0
                    STRUCT_FIELD[14 + j][i] = 0
                j += 1
        self.PROTECTED_FIELD = [1000] * 28
        for i in range(28):
            PROTECTED_FIELD[i] = [1000] * 28
        for i in range(0, 14):
            j = 0
            while j <= i:
                PROTECTED_FIELD[13 - j][i] = 0
                PROTECTED_FIELD[14 + j][i] = 0
                j += 1

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

    def build_neeeded_walls(self, game_state, curr_y):
        walls_built = [[25, 13], [2, 13], [2, 12], [25, 12]]
        for x in range(28):
            if STRUCT_FIELD[x][curr_y] == 2 or STRUCT_FIELD[x][curr_y] == 6:
                walls_built.append([x, curr_y + 1])
        self.spawn_and_mark(game_state, walls_built, WALL)
        game_state.attempt_remove(walls_built)

    def get_less_defended_rating(self, curr_y):
        minimal_vage = 100
        answer = []
        for i in range(28):
            answer.append(PROTECTED_FIELD[i][curr_y])
            if minimal_vage > PROTECTED_FIELD[i][curr_y] and STRUCT_FIELD[i][curr_y] == 0:
                minimal_vage = PROTECTED_FIELD[i][curr_y]
        return minimal_vage

    def get_most_defended_x(self, curr_y):
        maximal_vage = -1
        answer = []
        gamelib.util.debug_write("      Defended line:")
        for i in range(28):
            answer.append(PROTECTED_FIELD[i][curr_y])
            if maximal_vage < PROTECTED_FIELD[i][curr_y] < 500 and STRUCT_FIELD[i][curr_y] == 0:
                maximal_vage = PROTECTED_FIELD[i][curr_y]
        gamelib.util.debug_write(str(answer))
        return maximal_vage

    def choose_best_tower_loco(self, game_state, curr_y):
        minimal_vage = self.get_less_defended_rating(curr_y)
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
            sum_of_loco = 1
            count_of_parts = 1
            for loco in location_in_range:
                sum_of_loco += PROTECTED_FIELD[loco[0]][loco[1]]
                count_of_parts += 1
            if count_of_parts == 0:
                sum_of_points.append(1000)
            else:
                sum_of_points.append(sum_of_loco / count_of_parts)
        min_sim = 1000
        index = 0
        for sum in sum_of_points:
            if min_sim > sum:
                index = sum_of_points.index(sum)
                min_sim = sum
        return best_loco[index]

    def choose_place_of_support(self, game_state, curr_y):
        most_profitable_place = [13, 10]
        maximal_rate = self.get_most_defended_x(curr_y)
        gamelib.util.debug_write("      Most defended x")
        gamelib.util.debug_write(maximal_rate)
        best_loco = self.get_all_locations_line_by_rate(curr_y, maximal_rate)
        gamelib.util.debug_write("      Best loco:")
        gamelib.util.debug_write(best_loco)
        #TODO Summury score = coverage ration * price current structures
        if len(best_loco) == 1:
            return best_loco[0]
        if len(best_loco) == 0:
            return most_profitable_place
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
            if STRUCT_FIELD[location[0]][location[1]] != 0 and STRUCT_FIELD[location[0]][location[1]] != 4 and STRUCT_FIELD[location[0]][location[1]] != 8 and STRUCT_FIELD[location[0]][location[1]] > -1:
                summa += STRUCT_FIELD[location[0]][location[1]]
        return summa

    def get_all_locations_line_by_rate(self, curr_y, rate):
        best_loco = []
        for i in range(28):
            if rate == PROTECTED_FIELD[i][curr_y] and STRUCT_FIELD[i][curr_y] == 0:
                best_loco.append([i, curr_y])
        return best_loco

    def defend_edges(self, game_state):
        first_need_walls = [[0, 13], [1, 13], [27, 13], [26, 13]]
        first_need_towers = [[1, 12], [26, 12]]
        missing_towers = []
        for tower in first_need_towers:
            if not self.is_unit_placed(game_state, tower):
                missing_towers.append(tower)
        self.spawn_and_mark(game_state, missing_towers, TURRET)
        self.upgrade_and_mark(game_state,missing_towers, TURRET)
        missing_walls = []
        removed_walls = []
        for wall in first_need_walls:
            if not self.is_unit_placed(game_state, wall):
                missing_walls.append(wall)
            else:
                if self.get_health_of_structure(game_state, wall) < 100:
                    removed_walls.append(wall)
        if len(removed_walls) != 0:
            game_state.attempt_remove(removed_walls)
        self.spawn_and_mark(game_state, missing_walls, WALL)
        self.upgrade_and_mark(game_state, missing_walls, WALL)

    def place_wall_close_to_turrles(self, game_state, turret):
        turret[1] += 1
        self.spawn_and_mark(game_state, turret, WALL)

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
        real_array = self.make_false_array_real(unit_array)
        for unit in real_array:
            if game_state.attempt_spawn(unit_type, unit) > 1:
                self.map_units(game_state, unit, unit_type)

    def upgrade_and_mark(self, game_state, unit_array, unit_type):
        real_array = self.make_false_array_real(unit_array)
        for unit in real_array:
            if game_state.attempt_upgrade(unit) > 0:
                self.map_units(game_state, unit, unit_type)

    def build_defences(self, game_state):
        # Place turrets that attack enemy units
        turret_locations = [[3, 11], [12, 11], [24, 11]]
        wall_updates = [[12, 12], [3, 12]]
        wall_locations = [[0, 13], [1, 13], [26, 13], [27, 13], [24, 12]]
        #support_locations = []

        self.spawn_and_mark(game_state, turret_locations, TURRET)
        self.spawn_and_mark(game_state, wall_locations, WALL)
        self.spawn_and_mark(game_state, wall_updates, WALL)
        self.upgrade_and_mark(game_state, wall_updates, WALL)
        self.upgrade_and_mark(game_state, turret_locations, TURRET)

    def fox_defense(self, game_state):
        if game_state.turn_number >= 8:
            return False
        first_walls_needed = [[0, 13], [1, 12], [27, 13], [26, 12]]
        first_turrets_placed = [[16, 9], [11, 9],  [4, 11], [6, 10], [9, 10], [18, 10], [21, 10], [23, 11]]
        first_supports_placed = [[6, 9], [21, 9]]

        if game_state.turn_number == 0:
            self.spawn_and_mark(game_state, first_supports_placed, SUPPORT)
            self.spawn_and_mark(game_state, first_turrets_placed, TURRET)
            self.spawn_and_mark(game_state, first_walls_needed, WALL)
            game_state.attempt_spawn(INTERCEPTOR, [3, 10], 1)
            game_state.attempt_spawn(INTERCEPTOR, [24, 10], 1)
            return True

        if game_state.turn_number == 4:
            if not self.is_unit_placed(game_state, [0, 13]):
                self.spawn_and_mark(game_state, [10, 13], WALL)
            else:
                self.upgrade_and_mark(game_state, [10, 13], WALL)
            if not self.is_unit_placed(game_state, [27, 13]):
                self.spawn_and_mark(game_state, [27, 13], WALL)
            else:
                self.upgrade_and_mark(game_state, [27, 13], WALL)
            self.spawn_and_mark(game_state, [[26, 13], [1, 13]], WALL)
            game_state.attempt_spawn(DEMOLISHER, [22, 8], 2)
            game_state.attempt_spawn(INTERCEPTOR, [3, 10], 1)
            game_state.attempt_spawn(INTERCEPTOR, [7, 6], 1)
            return True

        if game_state.turn_number == 6:
            new_turrets = [[10, 10], [14, 10], [17, 10]]
            self.spawn_and_mark(game_state, new_turrets, TURRET)
            self.upgrade_and_mark(game_state, new_turrets, TURRET)
            game_state.attempt_spawn(INTERCEPTOR, [23, 9], 1)
            game_state.attempt_spawn(INTERCEPTOR, [4, 9], 1)
            return True

        if game_state.turn_number == 7:
            new_walls = [[6, 11], [10, 11], [14, 11], [17, 10], [21, 11]]
            self.spawn_and_mark(game_state, new_walls, WALL)
            upgr_walls = [[26, 13], [1, 13]]
            self.upgrade_and_mark(game_state, upgr_walls, WALL)
            game_state.attempt_spawn(INTERCEPTOR, [23, 9], 1)
            game_state.attempt_spawn(INTERCEPTOR, [4, 9], 1)
            game_state.attempt_remove([[1, 12], [26, 12]])
            return True

        if game_state.turn_number >= 1:
            missed_walls = []
            for unit in first_walls_needed:
                try:
                    first_walls_needed.index([unit[0], unit[1]])
                except ValueError:
                    missed_walls.append([unit[0], unit[1]])
            missed_turrets = []
            for unit in first_turrets_placed:
                try:
                    first_turrets_placed.index([unit[0], unit[1]])
                except ValueError:
                    missed_turrets.append([unit[0], unit[1]])
            left_destroyed = []
            right_destroyed = []
            for unit in missed_turrets:
                if unit[0] <= 13:
                    left_destroyed.append(unit)
                else:
                    right_destroyed.append(unit)
            if len(left_destroyed) > 0:
                game_state.attempt_spawn(INTERCEPTOR, [6, 7], 1)
                game_state.attempt_spawn(INTERCEPTOR, [3, 10], 1)
            else:
                game_state.attempt_spawn(INTERCEPTOR, [3, 10], 1)
            if len(right_destroyed) > 0:
                game_state.attempt_spawn(INTERCEPTOR, [24, 10], 1)
                game_state.attempt_spawn(INTERCEPTOR, [20, 6], 1)
            else:
                game_state.attempt_spawn(INTERCEPTOR, [24, 10], 1)

            if game_state.turn_number == 1:
                if self.is_unit_placed(game_state, [6, 9]):
                    self.upgrade_and_mark(game_state, [6, 9], SUPPORT)
                else:
                    self.spawn_and_mark(game_state, [6, 9], SUPPORT)


            if game_state.turn_number == 2:
                if self.is_unit_placed(game_state, [21, 9]):
                    self. upgrade_and_mark(game_state, [21, 9], SUPPORT)
                else:
                    self.spawn_and_mark(game_state, [21, 9], SUPPORT)

            if game_state.turn_number == 3:
                if self.is_unit_placed(game_state, [21, 10]):
                    self. upgrade_and_mark(game_state, [21, 10], TURRET)
                else:
                    self.spawn_and_mark(game_state, [21, 10], TURRET)

                if self.is_unit_placed(game_state, [6, 10]):
                    self. upgrade_and_mark(game_state, [6, 10], TURRET)
                else:
                    self.spawn_and_mark(game_state, [6, 10], TURRET)


            if game_state.turn_number == 5:
                removing_turrets = [[4, 11], [9, 10], [11, 9], [16, 9], [23, 11], [18, 10]]
                game_state.attempt_remove(removing_turrets)
            return True

    def build_the_pass(self, game_state):
        left_x = 12
        reight_x = 15
        curr_y = 10
        bottom_y = 4
        while (self.is_unit_placed(game_state, [left_x, curr_y]) and self.is_unit_placed(game_state, [reight_x, curr_y])) and curr_y >= bottom_y:
            curr_y -= 1
        self.spawn_and_mark(game_state, [[left_x, curr_y], [reight_x, curr_y]], SUPPORT)
        self.upgrade_and_mark(game_state, [[left_x, curr_y], [reight_x, curr_y]], SUPPORT)

    def spawn_interceptors(self, game_state):
        holes = self.find_least_secured_locations(game_state, [9, 10, 11])
        starting_points = self.find_best_interceptor_starting_points(game_state, holes)
        game_state.attempt_spawn(INTERCEPTOR, starting_points[0])
        for i in range(5 - len(starting_points[0])):
            game_state.attempt_spawn(INTERCEPTOR, starting_points[1][i])

    def find_least_secured_locations(self, game_state, y_list):
        min_rating = 100
        min_y_list = []
        for y in y_list:
            cur_rating = self.get_less_defended_rating(y)
            if min_rating == cur_rating:
                min_y_list.append(y)
            elif min_rating > cur_rating:
                min_rating = cur_rating
                min_y_list = [y]

        res = []
        for y in min_y_list:
            res += self.get_all_locations_line_by_rate(y, min_rating)

        return res
    
    def find_best_interceptor_starting_points(self, game_state, least_secured):
        """Potentially very slow"""
        # get unblocked edge locations
        edge_locations = game_state.game_map.edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        edge_locations = self.filter_blocked_locations(edge_locations, game_state)
        # ckeck coverage of every possible path
        coverage_list = [[]] * len(least_secured)
        for loc in edge_locations:
            self.update_coverage(game_state, loc, least_secured, coverage_list)
        # filter from unreachable points
        coverage_list = [x for x in filter(lambda x: len(x) > 0, coverage_list)]
        coverage_list.sort(key=lambda x: len(x))
        # get starting locations
        res = [[], []]
        while len(coverage_list) > 0:
            if len(coverage_list[0]) == 1:
                res[0].append(coverage_list[0][0])
                coverage_list = self.filter_from_covered(coverage_list, coverage_list[0][0])
            else:
                point = self.find_most_covering(coverage_list)
                res[1].append(point)
                coverage_list = self.filter_from_covered(coverage_list, point)

        return res

    def update_coverage(self, game_state, starting_location, locations_to_cover, coverage_list):
        path = game_state.find_path_to_edge(starting_location)
        for p in path:
            covered = game_state.game_map.get_locations_in_range(p, 4.5)
            for i in range(len(locations_to_cover)):
                if locations_to_cover[i] in covered:
                    coverage_list[i].append(starting_location)        
    
    def filter_from_covered(self, coverage_list, starting_loc):
        res = []
        for cov in coverage_list:
            if starting_loc not in cov:
                res.append(cov)

        return res
    
    def find_most_covering(self, coverage_list):
        points_set = set()
        for cov in coverage_list:
            for item in cov:
                points_set.add(tuple(item))
        res = []
        max_count = 0
        for p in points_set:
            count = 0
            point = list(p)
            # get covered points count
            for cov in coverage_list:
                if point in cov:
                    count += 1
            # update list
            if count > max_count:
                res = point
                max_count = count

        return res


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
