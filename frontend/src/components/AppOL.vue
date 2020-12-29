<template>
  <div style="background-color: orange">

    <!-- ========== map & view ========= -->
    <vl-map  :load-tiles-while-animating="true"
             :load-tiles-while-interacting="true"
             data-projection="EPSG:4326"
             ref="map"
              @mounted="onMapMounted"
           >

    <vl-view ref="view"
             :zoom.sync="zoom"
             :center.sync="center"
             :rotation.sync="rotation"></vl-view>

      <!-- ========== layers ========= -->
      <vl-layer-tile id="osm">
        <vl-source-osm></vl-source-osm>
      </vl-layer-tile>

      <!-- flight path features layer -->
      <vl-layer-vector >
        <vl-source-vector :url="geojsonUrl"
                          :features.sync="geojFeatures" />
        <vl-style-func :factory="geojStyleFuncFactory"></vl-style-func>
      </vl-layer-vector>

      <!-- kml features layer -->
      <vl-layer-vector >
          <vl-source-vector :url="kmlUrl"
                            :format-factory="kmlFormatFactory" />
      </vl-layer-vector>

      <!-- asdex layer -->
      <vl-layer-vector >
        <vl-source-vector :url="asdexUrl"
                          :features.sync="asdexFeatures" />
        <vl-style-func :factory="asdexStyleFuncFac" />
      </vl-layer-vector>

      <!-- ========== popup ========= -->
   <vl-interaction-select :features.sync="geojFeatures"></vl-interaction-select>

    <vl-overlay v-for="feature in geojFeatures"
                :key="feature.id"
                :position="feature.geometry.coordinates[0]">
      <div style="background: #ccf">
        {{ feature.properties.display }}
      </div>
    </vl-overlay>

    <!-- display in popup now formed by python lambda -->
        <!-- Feature ID: {{ feature.id }}
        Name: {{ feature.properties.ORIG_TIME }}
        Src: {{ feature.properties.SOURCE_TYPE }} -->

      <!-- ========== end ========= -->
    </vl-map>

  </div>
</template>

<script>

// $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

import ZoomSlider from 'ol/control/ZoomSlider'
import ScaleLine  from 'ol/control/ScaleLine'
import Stroke     from 'ol/style/Stroke'
import Style      from 'ol/style/Style'
import KML        from 'ol/format/KML'

// ==========================================================

const methods = {

    onMapMounted () {
      // now ol.Map instance is ready and we can work with it directly
      this.$refs.map.$map.getControls().extend([
        new ScaleLine(),
        new ZoomSlider(),
      ])
    },

    kmlFormatFactory () {
      //return new ol.format.KML()
      return new KML()
    },

    // ------------ attempt to color lines
    asdexStyleFuncFac() {
      const activestyle = new Style({
          stroke: new Stroke({
            color: 'magenta',
            width: 3.25,
          })
      })

      return (feature) => {
        // help: using feature is pointless;
        // but what is an 'arrow function' with no args???
        if (feature.get('acid')) {
          return activestyle
        }
        return activestyle
     }
    },
    // ------------ attempt to color lines
    geojStyleFuncFactory() {
      const unkStyle = new Style({
          stroke: new Stroke({ color: 'black', width: 3.25, })
      })

      return (feature) => {
        if (feature.get('SOURCE_TYPE')) {
          if (feature.get('SOURCE_TYPE')=='S') {
            return new Style({ stroke: new Stroke({ color: 'red', width: 3.25, }) })
          }
          if (feature.get('SOURCE_TYPE')=='F') {
            return new Style({ stroke: new Stroke({ color: 'blue', width: 3.25, }) })
          }
          if (feature.get('SOURCE_TYPE')=='A') {
            return new Style({ stroke: new Stroke({ color: 'magenta', width: 3.25, }) })
          }
          return unkStyle;
        }
        return unkStyle;
     }
   }
}

// ==========================================================

var KSTL = [-90.3700289, 38.7486972];

export default {
    methods,
    data () {
      return {
        zoom: 5,
        center: KSTL,
        rotation: 0,

        geojsonUrl: '',
        geojFeatures: [],

        kmlUrl: '',

        asdexUrl: '',
        asdexFeatures: []

      }
    },

// ==========================================================

  mounted () {

    // -------------------------
    this.$root.$on('geojsonurl', (the_query) => {
      console.log("geojson:"+the_query);

      this.geojsonUrl = the_query;   // << that's all we have to do!
    })
    // -------------------------
    this.$root.$on('kmlurl', (the_query) => {
      console.log("kml:"+the_query);

      this.kmlUrl = the_query;
    })
    // -------------------------
    this.$root.$on('asdexurl', (the_query) => {
      console.log("asdex::"+the_query);

      this.asdexUrl = the_query;
    })
    // -------------------------
  },

// ==========================================================
}

</script>

