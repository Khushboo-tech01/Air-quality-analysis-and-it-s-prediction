export const LOCATION_DATA = {
  India: {
    Delhi: ["New Delhi", "Delhi", "Dwarka", "Rohini", "Karol Bagh"],
    Rajasthan: ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner"],
    Maharashtra: ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad"],
    Gujarat: ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar"],
    Karnataka: ["Bangalore", "Mysore", "Mangalore", "Hubli", "Belgaum"],
    Telangana: ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Noida", "Ghaziabad"],
    Haryana: ["Gurugram", "Faridabad", "Panipat", "Ambala"],
    Punjab: ["Amritsar", "Ludhiana", "Jalandhar", "Patiala"],
  },
  "United Kingdom": {
    England: ["London", "Manchester", "Birmingham", "Liverpool", "Leeds", "Bristol"],
    Scotland: ["Edinburgh", "Glasgow", "Aberdeen", "Dundee"],
    Wales: ["Cardiff", "Swansea", "Newport"],
    "Northern Ireland": ["Belfast", "Derry"],
  },
  "United States": {
    California: ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "San Jose"],
    "New York": ["New York", "Buffalo", "Rochester", "Albany"],
    Texas: ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
    Illinois: ["Chicago", "Springfield", "Peoria"],
    Washington: ["Seattle", "Spokane", "Tacoma"],
  },
  Canada: {
    Ontario: ["Toronto", "Ottawa", "Mississauga", "Hamilton"],
    Quebec: ["Montreal", "Quebec City", "Laval"],
    "British Columbia": ["Vancouver", "Victoria", "Surrey"],
  },
  Australia: {
    "New South Wales": ["Sydney", "Newcastle", "Wollongong"],
    Victoria: ["Melbourne", "Geelong", "Ballarat"],
    Queensland: ["Brisbane", "Gold Coast", "Cairns"],
  },
};

export function countryOptions() {
  return Object.keys(LOCATION_DATA).map((name) => ({ value: name, label: name }));
}

export function stateOptions(country) {
  return Object.keys(LOCATION_DATA[country] || {}).map((name) => ({ value: name, label: name }));
}

export function cityOptions(country, state) {
  const states = LOCATION_DATA[country] || {};
  const cities = state ? states[state] || [] : Object.values(states).flat();
  return [...new Set(cities)].map((name) => ({ value: name, label: name }));
}
