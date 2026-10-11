import gulp from 'gulp';
import sourcemaps from 'gulp-sourcemaps';
import babel from 'gulp-babel';
import gulpSass from 'gulp-sass';
import * as dartSass from 'sass';

const sass = gulpSass(dartSass);

const paths = {
    inBase: './spongeauth/static',
    outBase: './spongeauth/static-build',

    styles: '/styles',
    appStyle: '/styles/app.scss',

    fonts: '/fonts',

    scripts: '/scripts',
    appScript: '/scripts/app.js',

    images: '/images',
};

function styles() {
    return gulp.src(paths.inBase + paths.styles + '/*.scss')
        .pipe(sourcemaps.init())
        .pipe(sass({ loadPaths: ['node_modules'], quietDeps: true }))
        .pipe(sourcemaps.write('../maps/'))
        .pipe(gulp.dest(paths.outBase + paths.styles));
}

function fonts() {
    return gulp.src([
        './node_modules/font-awesome/fonts/fontawesome-webfont.*',
        './node_modules/bootstrap-sass/assets/fonts/bootstrap/glyphicons-halflings-regular.*',
    ], { encoding: false }).pipe(gulp.dest(paths.outBase + paths.fonts));
}

function images() {
    return gulp.src(paths.inBase + paths.images + '/**', { encoding: false })
        .pipe(gulp.dest(paths.outBase + paths.images));
}

function scripts() {
    return gulp.src(paths.inBase + paths.appScript)
        .pipe(sourcemaps.init())
        .pipe(babel({ presets: ['@babel/preset-env'] }))
        .pipe(sourcemaps.write('../maps/'))
        .pipe(gulp.dest(paths.outBase + paths.scripts));
}

function watch() {
    gulp.watch(paths.inBase + paths.styles + '/**', styles);
    gulp.watch(paths.inBase + paths.scripts + '/**', scripts);
    gulp.watch(paths.inBase + paths.images + '/**', images);
}

export const build = gulp.parallel(styles, fonts, scripts, images);
export { watch };
export default gulp.series(build, watch);
