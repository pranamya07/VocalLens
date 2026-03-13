# agents/nlu_agent.py
"""
Intelligent Natural Language Understanding Agent
Understands ANY query with world knowledge and reasoning
"""

import re
from datetime import datetime
import json

class NLUAgent:
    """
    Parses ANY query using world knowledge and context
    """
    
    def __init__(self):
        # World knowledge - how things relate to each other
        self.world_knowledge = {
            'events': {
                'wedding': {
                    'description': 'A ceremony where two people get married',
                    'elements': ['bride', 'groom', 'cake', 'ceremony', 'reception', 'flowers'],
                    'visual_cues': ['wedding_dress', 'veil', 'bouquet', 'rings', 'mandap', 'church'],
                    'roles': {
                        'bride': {'gender': 'female', 'importance': 10, 'visual': 'wedding_dress'},
                        'groom': {'gender': 'male', 'importance': 10, 'visual': 'tuxedo'},
                        'bridesmaids': {'gender': 'female', 'importance': 7, 'visual': 'matching_dresses'},
                        'parents': {'gender': 'both', 'importance': 8, 'visual': 'formal_wear'},
                        'guests': {'gender': 'both', 'importance': 5, 'visual': 'party_attire'}
                    },
                    'cultural_variants': {
                        'indian': ['saptapadi', 'sindoor', 'mehendi', 'mandap'],
                        'western': ['vows', 'aisle', 'officiant', 'church'],
                        'muslim': ['nikah', 'mehr', 'walima']
                    },
                    'date_pattern': 'single_day'
                },
                'birthday': {
                    'description': 'Celebration of someone\'s birth',
                    'elements': ['cake', 'candles', 'presents', 'party_hats', 'balloons'],
                    'visual_cues': ['cake_with_candles', 'gifts', 'happy_birthday_sign'],
                    'roles': {
                        'birthday_person': {'importance': 10, 'visual': 'center_of_attention'},
                        'guests': {'importance': 5, 'visual': 'party_attire'}
                    },
                    'date_pattern': 'single_day'
                },
                'graduation': {
                    'description': 'Completion of academic degree',
                    'elements': ['cap', 'gown', 'diploma', 'stage', 'family'],
                    'visual_cues': ['graduation_cap', 'graduation_gown', 'stage_background'],
                    'roles': {
                        'graduate': {'importance': 10, 'visual': 'cap_and_gown'},
                        'family': {'importance': 8, 'visual': 'proud_parents'}
                    },
                    'date_pattern': 'seasonal'  # May-June typically
                },
                'vacation': {
                    'description': 'Leisure trip away from home',
                    'elements': ['landmarks', 'hotels', 'beaches', 'mountains'],
                    'visual_cues': ['suitcases', 'tourist_poses', 'famous_landmarks'],
                    'roles': {
                        'travelers': {'importance': 8, 'visual': 'casual_clothes'}
                    },
                    'date_pattern': 'multiple_days'
                },
                'party': {
                    'description': 'Social gathering for celebration',
                    'elements': ['food', 'drinks', 'music', 'dancing', 'decorations'],
                    'visual_cues': ['party_lights', 'dancing', 'group_photos'],
                    'roles': {
                        'host': {'importance': 7, 'visual': 'organizer'},
                        'guests': {'importance': 6, 'visual': 'socializing'}
                    },
                    'date_pattern': 'single_day'
                }
            },
            
            'relationships': {
                'sister': {
                    'type': 'sibling',
                    'gender': 'female',
                    'possible_roles': ['bride', 'bridesmaid', 'guest', 'host'],
                    'family_level': 'immediate'
                },
                'brother': {
                    'type': 'sibling',
                    'gender': 'male',
                    'possible_roles': ['groom', 'groomsman', 'guest'],
                    'family_level': 'immediate'
                },
                'mother': {
                    'type': 'parent',
                    'gender': 'female',
                    'possible_roles': ['mother_of_bride', 'mother_of_groom', 'guest'],
                    'family_level': 'immediate'
                },
                'father': {
                    'type': 'parent',
                    'gender': 'male',
                    'possible_roles': ['father_of_bride', 'father_of_groom', 'guest'],
                    'family_level': 'immediate'
                },
                'friend': {
                    'type': 'social',
                    'gender': 'unknown',
                    'possible_roles': ['bridesmaid', 'groomsman', 'guest', 'party_attendee'],
                    'family_level': 'social'
                },
                'wife': {
                    'type': 'spouse',
                    'gender': 'female',
                    'possible_roles': ['bride', 'partner'],
                    'family_level': 'immediate'
                },
                'husband': {
                    'type': 'spouse',
                    'gender': 'male',
                    'possible_roles': ['groom', 'partner'],
                    'family_level': 'immediate'
                },
                'daughter': {
                    'type': 'child',
                    'gender': 'female',
                    'possible_roles': ['bride', 'graduate', 'birthday_person'],
                    'family_level': 'immediate'
                },
                'son': {
                    'type': 'child',
                    'gender': 'male',
                    'possible_roles': ['groom', 'graduate', 'birthday_person'],
                    'family_level': 'immediate'
                }
            },
            
            'locations': {
                'beach': {'type': 'outdoor', 'visual_cues': ['sand', 'water', 'waves']},
                'mountain': {'type': 'outdoor', 'visual_cues': ['peaks', 'snow', 'trees']},
                'city': {'type': 'urban', 'visual_cues': ['buildings', 'streets', 'lights']},
                'home': {'type': 'indoor', 'visual_cues': ['furniture', 'rooms']},
                'restaurant': {'type': 'indoor', 'visual_cues': ['tables', 'food', 'waiters']},
                'park': {'type': 'outdoor', 'visual_cues': ['grass', 'trees', 'benches']}
            }
        }
        
        # Common patterns in queries
        self.patterns = {
            'possession': re.compile(r'(\w+)\'s\s+(\w+)'),
            'relationship': re.compile(r'(my|your|his|her|their)\s+(\w+)'),
            'time_period': re.compile(r'(since|from|in|during)\s+(\w+)'),
            'event': re.compile(r'\b(' + '|'.join(self.world_knowledge['events'].keys()) + r')\b', re.I),
            'location': re.compile(r'\b(' + '|'.join(self.world_knowledge['locations'].keys()) + r')\b', re.I),
            'date': re.compile(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|20\d{2})\b', re.I)
        }
    
    def process(self, query, context=None):
        """
        Main entry point - process ANY query intelligently
        """
        query_lower = query.lower().strip()
        
        # Step 1: Identify main intent
        intent = self._identify_intent(query_lower)
        
        # Step 2: Extract all entities with relationships
        entities = self._extract_entities_with_context(query_lower)
        
        # Step 3: Identify relationships between entities
        relationships = self._identify_relationships(query_lower, entities)
        
        # Step 4: Identify what information is MISSING
        missing_info = self._identify_missing_info(entities, relationships, context)
        
        # Step 5: Generate reasoning steps (for UI)
        reasoning = self._generate_reasoning(query, entities, relationships, missing_info)
        
        # Step 6: Create execution plan
        execution_plan = self._create_execution_plan(intent, entities, relationships, missing_info)
        
        return {
            'intent': intent,
            'entities': entities,
            'relationships': relationships,
            'missing_info': missing_info,
            'reasoning': reasoning,
            'execution_plan': execution_plan,
            'original_query': query
        }
    
    def _identify_intent(self, query):
        """What does user want to DO?"""
        # Check for action verbs
        if any(word in query for word in ['make', 'create', 'generate', 'build']):
            return 'create_album'
        elif any(word in query for word in ['show', 'find', 'get', 'search', 'display']):
            return 'search'
        elif any(word in query for word in ['slideshow', 'play', 'video']):
            return 'slideshow'
        elif any(word in query for word in ['tag', 'label', 'name', 'identify']):
            return 'tag'
        elif any(word in query for word in ['remember', 'save', 'store', 'learn']):
            return 'learn'
        elif any(word in query for word in ['select', 'choose', 'pick']):
            return 'identify'
        else:
            return 'search'  # default
    
    def _extract_entities_with_context(self, query):
        """Extract all entities with their context and relationships"""
        entities = {
            'people': [],
            'events': [],
            'locations': [],
            'dates': [],
            'objects': [],
            'time_periods': []
        }
        
        words = query.split()
        
        # Extract people with relationships
        for match in self.patterns['relationship'].finditer(query):
            possessor, relation = match.groups()
            if relation in self.world_knowledge['relationships']:
                entities['people'].append({
                    'relation': relation,
                    'possessor': possessor,
                    'metadata': self.world_knowledge['relationships'][relation],
                    'needs_identification': True,
                    'confidence': 0.7
                })
        
        # Direct relationship mentions (e.g., "sister" without possessor)
        for word in words:
            if word in self.world_knowledge['relationships']:
                # Check if already added
                if not any(p.get('relation') == word for p in entities['people']):
                    entities['people'].append({
                        'relation': word,
                        'possessor': 'unknown',
                        'metadata': self.world_knowledge['relationships'][word],
                        'needs_identification': True,
                        'confidence': 0.6
                    })
        
        # Extract events
        for match in self.patterns['event'].finditer(query):
            event = match.group(1).lower()
            entities['events'].append({
                'type': event,
                'metadata': self.world_knowledge['events'][event],
                'confidence': 0.8,
                'possible_dates': []
            })
        
        # Extract locations
        for match in self.patterns['location'].finditer(query):
            location = match.group(1).lower()
            entities['locations'].append({
                'name': location,
                'metadata': self.world_knowledge['locations'][location],
                'confidence': 0.8
            })
        
        # Extract dates
        for match in self.patterns['date'].finditer(query):
            date = match.group(1).lower()
            entities['dates'].append({
                'value': date,
                'type': 'month' if date in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'] else 'year',
                'confidence': 0.9
            })
        
        # Extract time periods (since, from, etc.)
        for match in self.patterns['time_period'].finditer(query):
            period_type, value = match.groups()
            entities['time_periods'].append({
                'type': period_type,
                'value': value,
                'confidence': 0.7
            })
        
        return entities
    
    def _identify_relationships(self, query, entities):
        """Identify how entities relate to each other"""
        relationships = []
        
        # Possessive relationships (sister's wedding)
        for match in self.patterns['possession'].finditer(query):
            possessor, possessed = match.groups()
            
            # Check if possessor is a person
            person = next((p for p in entities['people'] if p['relation'] == possessor), None)
            if person:
                # Check if possessed is an event
                event = next((e for e in entities['events'] if e['type'] == possessed), None)
                if event:
                    relationships.append({
                        'type': 'possession',
                        'person': person,
                        'event': event,
                        'role': self._infer_role(person, event),
                        'confidence': 0.8
                    })
        
        # "in" relationships (sister in wedding)
        in_pattern = re.compile(r'(\w+)\s+in\s+(\w+)(?:\'s)?\s+(\w+)')
        for match in in_pattern.finditer(query):
            person_word, _, event_word = match.groups()
            
            person = next((p for p in entities['people'] if p['relation'] == person_word), None)
            event = next((e for e in entities['events'] if e['type'] == event_word), None)
            
            if person and event:
                relationships.append({
                    'type': 'participation',
                    'person': person,
                    'event': event,
                    'role': self._infer_role(person, event),
                    'confidence': 0.7
                })
        
        return relationships
    
    def _infer_role(self, person, event):
        """Infer what role a person might play in an event"""
        event_type = event['type']
        person_relation = person['relation']
        
        if event_type == 'wedding':
            if person_relation in ['sister', 'daughter']:
                return 'possible_bride'
            elif person_relation in ['mother', 'father']:
                return 'parent_of_bride_or_groom'
            elif person_relation == 'brother':
                return 'possible_groomsman'
            else:
                return 'guest'
        
        elif event_type == 'birthday':
            if person_relation in ['me', 'i', 'my']:
                return 'birthday_person'
            else:
                return 'guest'
        
        elif event_type == 'graduation':
            if person_relation in ['sister', 'brother', 'daughter', 'son']:
                return 'graduate'
            else:
                return 'family_member'
        
        return 'attendee'
    
    def _identify_missing_info(self, entities, relationships, context=None):
        """What don't we know that we need to know?"""
        missing = []
        
        # Check for people that need identification
        for person in entities.get('people', []):
            if person.get('needs_identification'):
                # Check if we already know this person from context
                known = False
                if context and 'known_people' in context:
                    if person['relation'] in context['known_people']:
                        known = True
                
                if not known:
                    missing.append({
                        'type': 'identify_person',
                        'person': person['relation'],
                        'context': person,
                        'question': f"I need to know which person in your photos is your {person['relation']}. Please select photos where {person['relation']} appears.",
                        'importance': 'high'
                    })
        
        # Check for ambiguous events (multiple possible)
        # This will be checked by database - are there multiple events of this type?
        # For now, we'll mark as potential missing info
        
        return missing
    
    def _generate_reasoning(self, query, entities, relationships, missing_info):
        """Generate human-readable reasoning steps for UI"""
        steps = []
        
        steps.append(f"Analyzing query: '{query}'")
        
        if entities['people']:
            people = [p['relation'] for p in entities['people']]
            steps.append(f"Identified people: {', '.join(people)}")
        
        if entities['events']:
            events = [e['type'] for e in entities['events']]
            steps.append(f"Identified events: {', '.join(events)}")
        
        if entities['locations']:
            locations = [l['name'] for l in entities['locations']]
            steps.append(f"Identified locations: {', '.join(locations)}")
        
        if entities['dates']:
            dates = [d['value'] for d in entities['dates']]
            steps.append(f"Identified dates: {', '.join(dates)}")
        
        if relationships:
            steps.append(f"Understood relationships: {len(relationships)} connections between entities")
        
        if missing_info:
            steps.append(f"Missing information detected: {len(missing_info)} items need clarification")
            for info in missing_info:
                if info['type'] == 'identify_person':
                    steps.append(f"  • Need to identify: {info['person']}")
        else:
            steps.append("All information available - proceeding with search")
        
        return steps
    
    def _create_execution_plan(self, intent, entities, relationships, missing_info):
        """Create step-by-step plan to fulfill request"""
        plan = []
        
        # Step 1: Handle missing information first
        if missing_info:
            plan.append({
                'stage': 'gather_info',
                'actions': missing_info,
                'next': 'search_after_confirmation'
            })
            return plan
        
        # Step 2: If we have all info, proceed with search/creation
        plan.append({
            'stage': 'execute',
            'intent': intent,
            'search_criteria': {
                'people': [p['relation'] for p in entities.get('people', [])],
                'events': [e['type'] for e in entities.get('events', [])],
                'locations': [l['name'] for l in entities.get('locations', [])],
                'dates': [d['value'] for d in entities.get('dates', [])]
            }
        })
        
        return plan
if __name__ == "__main__":
    nlu = NLUAgent()
    result = nlu.process("show me birthday photos in Mumbai")
    print(result)