<script setup>
import { ref, onMounted } from 'vue'
import { fabric } from 'fabric';
import axios from 'axios';
import maplibregl from 'maplibre-gl';

const colors = {
    building: 'brown',
    street: 'gray',
    vegetation: 'green'
}

let canvas;
let map;
const shapes = ref([]);
let idCounter = 0;
let markers = [];
const loading = ref(false);

onMounted(() => {
    canvas = new fabric.Canvas('canvas');
    map = new maplibregl.Map({
          container: 'map',
          style: import.meta.env.VITE_TILES_URL,
          center: [38.0021, 48.5889],
          zoom: 11
      });

      console.log(map)
    map.on('load', () => console.log(1))
})

function addShape(shape) {
    const rect = new fabric.Rect({
        id: idCounter,
        top: 100,
        left: 100,
        width: 60,
        height: 70,
        fill: colors[shape],
    });
    canvas.add(rect);

    shapes.value.push({
        id: idCounter,
        type: shape,
        length: '',
        distance: ''
    });

    idCounter++;
}

function clearMap() {
    for (const marker of markers) {
        marker.remove()
    }
    markers = [];
}

function clearAll() {
    shapes.value = [];
    canvas.clear();
    clearMap();
    idCounter = 0;
}

async function searchLocations() {
    loading.value = true;
    clearMap();
    const payload = [];
    for (const shape of canvas.getObjects()) {
        const height = shape.aCoords.br.y - shape.aCoords.tr.y;
        const width = shape.aCoords.br.x - shape.aCoords.bl.x
        const centroid = [shape.aCoords.bl.x + width / 2, shape.aCoords.tr.y + height / 2];
        const longShortRatio = height > width ? height / width : width / height;
        const longSide = shapes.value[shape.id].length;
        const shortSide = longSide / longShortRatio;
        const perimeter = (longSide + shortSide) * 2;
        const area = longSide * shortSide;
        const compactness = area / (perimeter ** 2);

        const azimuth = Math.atan2(centroid[1], centroid[0]) * 180 / Math.PI;
        
        const shapeRef = shapes.value[shape.id];
        payload.push({
            type: shapeRef.type,
            area: area,
            length: longSide,
            compactness: compactness,
            distance: shapeRef.distance,
            azimuth: azimuth
        })
    }

    const result = await axios.post(import.meta.env.VITE_API_URL, payload, {
        params: {
            access_token: import.meta.env.VITE_API_KEY
        }
    });
    const bounds = new maplibregl.LngLatBounds(result.data);

    for (const coord of result.data) {
        const popup = new maplibregl.Popup({ offset: 25 }).setText(`${coord[0].toFixed(4)}, ${coord[1].toFixed(4)}`);
        const marker = new maplibregl.Marker().setLngLat(coord).setPopup(popup).addTo(map);
        markers.push(marker);

        bounds.extend(coord);
    }
    
    loading.value = false;

    map.fitBounds(bounds, {
        padding: 50
    });
}
</script>

<template>
    <header>
        <div class="text-2xl text-white m-4">SketchMapper</div>
        <!--<img alt="Vue logo" class="logo" src="./assets/logo.svg" width="125" height="125" />-->
    </header>

    <div class="m-auto text-yellow-800 rounded-lg p-4 text-sm bg-yellow-50 ml-8" id="infobox">
        <span class="font-bold">This demo is currently limited to the city of Bakhmut! </span>
        <p>Using this tool, you can search for locations based on a sketch of buildings, streets and vegetation. For every shape, please provide the length of its longest edge and its closest distance to the center of the scene. Only rectangular shapes are currently supported. See <a href="https://github.com/mlkin/sketchmapper" class="font-bold">here</a> for examples.</p>
    </div>

  <main>
    <div id="canvas-wrapper">
        <canvas id="canvas" width="500" height="500"></canvas>
    </div>

    <div id="map-container">
        <div id="map"></div>
    </div>

    <div id="form-wrapper">
        <button class="py-2.5 px-5 mr-2 mb-2 text-sm font-medium text-gray-900 focus:outline-none bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-blue-700 focus:z-10 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:text-white dark:hover:bg-gray-700" @click="addShape('building')">Add building</button>
        <button class="py-2.5 px-5 mr-2 mb-2 text-sm font-medium text-gray-900 focus:outline-none bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-blue-700 focus:z-10 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:text-white dark:hover:bg-gray-700" @click="addShape('street')">Add street</button>
        <button class="py-2.5 px-5 mr-2 mb-2 text-sm font-medium text-gray-900 focus:outline-none bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-blue-700 focus:z-10 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:text-white dark:hover:bg-gray-700" @click="addShape('vegetation')">Add vegetation</button>

        <form @submit.prevent="searchLocations()" class="mt-8">
            <div v-for="shape in shapes">
                <span class="text-white text-lg font-semibold">Shape {{ shape.id + 1 }} ({{ shape.type.charAt(0).toUpperCase() + shape.type.slice(1) }})</span>

                <div class="grid md:grid-cols-2 md:gap-6">
                    <div class="relative z-0 w-full mb-6 group">
                        <label for="email" class="block mb-2 text-sm font-medium text-gray-100 dark:text-white">Longest side (m)</label>
                        <input v-model="shape.length" type="number" name="length" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500" required>
                    </div>
                    <div class="relative z-0 w-full mb-6 group">
                        <label for="email" class="block mb-2 text-sm font-medium text-gray-100 dark:text-white">Distance (m)</label>
                        <input v-model="shape.distance" type="number" name="distance" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500" required>
                    </div>
                </div>
            </div>
    
            <div v-if="shapes.length > 0" class="mt-8">
                <button type="submit" class="py-2.5 px-5 mr-2 mb-2 text-sm font-medium text-gray-900 focus:outline-none bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-blue-700 focus:z-10 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:text-white dark:hover:bg-gray-700">
                    <svg v-if="loading" aria-hidden="true" role="status" class="inline w-4 h-4 mr-3 text-gray-200 animate-spin dark:text-gray-600" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
                        <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="#1C64F2"/>
                    </svg>
                    <span v-else>
                        Search
                    </span></button>
                <button @click="clearAll" type="button" class="focus:outline-none text-white bg-red-700 hover:bg-red-800 focus:ring-4 focus:ring-red-300 font-medium rounded-lg text-sm px-5 py-2.5 mr-2 mb-2 dark:bg-red-600 dark:hover:bg-red-700 dark:focus:ring-red-900">Clear</button>
            </div>
        </form>
    </div>

  </main>
</template>

<style>
    body {
        background-color: #2b2b2b;
    }

    #canvas {
        padding: 0;
        background-color: aliceblue;
    }

    #canvas-wrapper {
        position: absolute;
        top: 250px;
        left: 600px;
        width: 500px;
        padding: 0;
    }

    #map {
        position: absolute;
        top: 0;
        bottom: 0;
        width: 100%;
    }

    #map-container {
        position: absolute;
        width: 500px;
        height: 500px;
        top: 250px;
        left: 1200px;
    }

    #form-wrapper {
        position: absolute;
        top: 250px;
        left: 30px;
    }

    #infobox {
        width: 800px;
    }
</style>
